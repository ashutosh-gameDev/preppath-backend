"""Student-facing ad serving: the active ad for a placement, and recording
impression/click events against it. See components/shared/ad-slot.tsx in
student-web for the call sites."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.ad import Ad, AdEvent
from app.models.course import Course
from app.models.user import User
from app.schemas.ad import AdEventIn, AdPublicOut

router = APIRouter(prefix="/ads", tags=["ads"])


@router.get("/active", response_model=AdPublicOut | None)
def get_active_ad(
    placement: str,
    course_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    conditions = [
        Ad.placement == placement,
        Ad.is_active.is_(True),
        or_(Ad.starts_at.is_(None), Ad.starts_at <= now),
        or_(Ad.ends_at.is_(None), Ad.ends_at >= now),
    ]
    # An untargeted ad (no courses picked) always qualifies; a targeted one
    # only qualifies when the caller's course_id is one of its targets - so
    # without a course_id at all (caller passed none), only untargeted ads show.
    if course_id is not None:
        conditions.append(or_(~Ad.courses.any(), Ad.courses.any(Course.id == course_id)))
    else:
        conditions.append(~Ad.courses.any())
    q = select(Ad).where(*conditions).order_by(Ad.priority.desc(), Ad.created_at.desc())
    return db.execute(q).scalars().first()


@router.post("/{ad_id}/events", status_code=204)
def record_ad_event(ad_id: uuid.UUID, payload: AdEventIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    db.add(AdEvent(ad_id=ad.id, event_type=payload.event_type))
    db.flush()
