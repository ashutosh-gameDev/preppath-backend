"""
Admin CRUD for `Ad` - the CRM's Ads Manager. Gated on require_admin (not
require_content_access): unlike questions/PYQ papers, ads are a revenue/UX
lever rather than everyday content work, so content_editor (intern)
accounts can't touch this.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.ad import Ad, AdEvent
from app.models.user import User
from app.schemas.ad import AdCreate, AdOut, AdUpdate
from app.schemas.common import Message
from app.services import storage_service
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/ads", tags=["admin:ads"])


@router.post("/upload-image")
async def upload_ad_image(file: UploadFile, admin: User = Depends(require_admin)):
    content = await file.read()
    try:
        url = storage_service.upload_ad_image(content, file.filename or "image.jpg", file.content_type or "")
    except storage_service.UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"url": url}


def _to_out(ad: Ad, impressions: int, clicks: int) -> AdOut:
    ctr = (clicks / impressions * 100) if impressions else 0.0
    return AdOut(
        id=ad.id, title=ad.title, image_url=ad.image_url, link_url=ad.link_url, body_text=ad.body_text,
        placement=ad.placement, priority=ad.priority, is_active=ad.is_active, starts_at=ad.starts_at,
        ends_at=ad.ends_at, created_at=ad.created_at, impressions=impressions, clicks=clicks, ctr=round(ctr, 2),
    )


@router.get("", response_model=list[AdOut])
def list_ads(
    placement: str | None = None,
    is_active: bool | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = select(Ad)
    if placement:
        q = q.where(Ad.placement == placement)
    if is_active is not None:
        q = q.where(Ad.is_active.is_(is_active))
    ads = db.execute(q.order_by(Ad.created_at.desc())).scalars().all()
    if not ads:
        return []

    rows = db.execute(
        select(
            AdEvent.ad_id,
            func.count(AdEvent.id).filter(AdEvent.event_type == "impression"),
            func.count(AdEvent.id).filter(AdEvent.event_type == "click"),
        )
        .where(AdEvent.ad_id.in_([a.id for a in ads]))
        .group_by(AdEvent.ad_id)
    ).all()
    stats = {ad_id: (impressions, clicks) for ad_id, impressions, clicks in rows}

    return [_to_out(ad, *stats.get(ad.id, (0, 0))) for ad in ads]


@router.post("", response_model=AdOut)
def create_ad(payload: AdCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ad = Ad(**payload.model_dump(), created_by=admin.id)
    db.add(ad)
    db.flush()
    log_action(db, admin.id, "create", "ad", ad.id)
    return _to_out(ad, 0, 0)


@router.patch("/{ad_id}", response_model=AdOut)
def update_ad(ad_id: uuid.UUID, payload: AdUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ad, field, value)
    db.flush()
    log_action(db, admin.id, "update", "ad", ad.id)

    impressions, clicks = db.execute(
        select(
            func.count(AdEvent.id).filter(AdEvent.event_type == "impression"),
            func.count(AdEvent.id).filter(AdEvent.event_type == "click"),
        ).where(AdEvent.ad_id == ad.id)
    ).one()
    return _to_out(ad, impressions, clicks)


@router.delete("/{ad_id}", response_model=Message)
def delete_ad(ad_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    db.delete(ad)  # cascades its ad_events
    db.flush()
    log_action(db, admin.id, "delete", "ad", ad_id)
    return Message(detail="Ad deleted")
