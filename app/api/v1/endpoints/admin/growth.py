"""
Admin visibility into the two growth/reward programs (refer-a-friend,
Study Timer monthly leaderboard) - read-only, the actual mechanics live in
services/referral_service.py and services/study_leaderboard_service.py.
The reward AMOUNTS/counts themselves are tuned via the generic
/admin/settings endpoint (keys "referral.*" and "study_leaderboard.*"),
not here.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.study_session import LeaderboardReward
from app.models.user import User
from app.schemas.growth import (
    AdminLeaderboardRewardOut,
    AdminStudyLeaderboardEntry,
    AdminStudyLeaderboardOut,
    TopReferrerOut,
)
from app.services.study_leaderboard_service import current_period, full_ranking_for_range

router = APIRouter(prefix="/admin/growth", tags=["admin:growth"])


@router.get("/referrals", response_model=list[TopReferrerOut])
def top_referrers(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(
        select(User.referred_by, func.count())
        .where(User.referred_by.is_not(None))
        .group_by(User.referred_by)
        .order_by(func.count().desc())
    ).all()
    out: list[TopReferrerOut] = []
    for referrer_id, count in rows:
        referrer = db.get(User, referrer_id)
        if referrer is None:
            continue
        out.append(TopReferrerOut(user_id=referrer.id, email=referrer.email, full_name=referrer.full_name, referred_count=count))
    return out


@router.get("/study-leaderboard", response_model=AdminStudyLeaderboardOut)
def study_leaderboard_admin(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    period, start, end = current_period(datetime.now(timezone.utc))
    ranking = full_ranking_for_range(db, start, end)
    current_standings = []
    for i, (uid, total_seconds) in enumerate(ranking[:50], start=1):
        u = db.get(User, uid)
        if u is None:
            continue
        current_standings.append(
            AdminStudyLeaderboardEntry(user_id=uid, email=u.email, full_name=u.full_name, total_seconds=total_seconds, rank=i)
        )

    reward_rows = db.execute(
        select(LeaderboardReward).order_by(LeaderboardReward.period.desc(), LeaderboardReward.rank_position)
    ).scalars().all()
    past_rewards = []
    for r in reward_rows:
        u = db.get(User, r.user_id)
        if u is None:
            continue
        past_rewards.append(
            AdminLeaderboardRewardOut(
                period=r.period, rank_position=r.rank_position, user_id=r.user_id, email=u.email,
                full_name=u.full_name, total_seconds=r.total_seconds, created_at=r.created_at,
            )
        )

    return AdminStudyLeaderboardOut(current_period=period, current_standings=current_standings, past_rewards=past_rewards)
