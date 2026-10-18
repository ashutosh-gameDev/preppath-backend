"""Student-facing ad serving: the active ad for a placement, and recording
impression/click events against it. See components/shared/ad-slot.tsx and
components/scrapbook/AdInterstitialReel.tsx in student-web for the call
sites."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
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

    # Course targeting narrows the SQL candidate set; location targeting and
    # impression/click caps are checked in Python below (json, not jsonb -
    # no containment-query precedent in this codebase, and this table is
    # small/CRM-managed, so a correlated WHERE isn't worth the complexity).
    # A course-qualifying candidate can still be disqualified by location or
    # a cap, so fetch every candidate (not just the top one) and fall
    # through to the next-best-priority ad instead of returning nothing.
    candidates = db.execute(
        select(Ad).where(*conditions).order_by(Ad.priority.desc(), Ad.created_at.desc())
    ).scalars().all()
    if not candidates:
        return None

    rows = db.execute(
        select(
            AdEvent.ad_id,
            func.count(AdEvent.id).filter(AdEvent.event_type == "impression"),
            func.count(AdEvent.id).filter(AdEvent.event_type == "click"),
        )
        .where(AdEvent.ad_id.in_([a.id for a in candidates]))
        .group_by(AdEvent.ad_id)
    ).all()
    stats = {ad_id: (impressions, clicks) for ad_id, impressions, clicks in rows}

    profile = user.profile
    city = profile.city if profile else None
    state = profile.state if profile else None

    for ad in candidates:
        if (ad.states or ad.cities) and not ((state and state in ad.states) or (city and city in ad.cities)):
            continue
        impressions, clicks = stats.get(ad.id, (0, 0))
        if ad.max_impressions is not None and impressions >= ad.max_impressions:
            continue
        if ad.max_clicks is not None and clicks >= ad.max_clicks:
            continue
        return ad
    return None


@router.post("/{ad_id}/events", status_code=204)
def record_ad_event(ad_id: uuid.UUID, payload: AdEventIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ad = db.get(Ad, ad_id)
    if ad is None:
        raise HTTPException(status_code=404, detail="Ad not found")
    db.add(AdEvent(ad_id=ad.id, event_type=payload.event_type))
    db.flush()
