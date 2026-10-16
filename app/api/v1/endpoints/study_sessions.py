"""
Study Timer: logs completed sessions and serves the monthly leaderboard.
See services/study_leaderboard_service.py for how the top-10 reward
actually gets paid out (lazily, on month rollover, no cron needed).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.study_session import StudySession
from app.models.user import User
from app.schemas.study_session import LeaderboardEntry, StudyLeaderboardOut, StudySessionCreate, StudySessionOut
from app.services import settings_service
from app.services.study_leaderboard_service import current_period, full_ranking_for_range, maybe_distribute_rewards

router = APIRouter(prefix="/study-sessions", tags=["study-sessions"])


@router.post("", response_model=StudySessionOut)
def log_study_session(
    payload: StudySessionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # One submission per calendar day (UTC) per user - keeps the leaderboard
    # a "did you have one real study block today" signal rather than
    # something padded by resetting the timer repeatedly. The frontend
    # gates the attempt itself behind a rewarded ad for non-Pro users;
    # this check is independent of that and always applies.
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    already_today = db.execute(
        select(StudySession.id).where(
            StudySession.user_id == user.id,
            StudySession.created_at >= today_start,
            StudySession.created_at < tomorrow_start,
        )
    ).first()
    if already_today:
        raise HTTPException(
            status_code=409, detail="You've already logged a study session today - come back tomorrow!"
        )

    session = StudySession(user_id=user.id, duration_seconds=max(0, payload.duration_seconds))
    db.add(session)
    db.flush()
    return session


@router.get("/leaderboard", response_model=StudyLeaderboardOut)
def get_leaderboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Settle last month's rewards (no-op after the first call following any
    # given month's rollover) before showing the CURRENT month's live race.
    maybe_distribute_rewards(db)

    winner_count = int(settings_service.get_setting(db, "study_leaderboard.winner_count"))
    reward_days = int(settings_service.get_setting(db, "study_leaderboard.reward_days"))
    period, start, end = current_period(datetime.now(timezone.utc))
    ranking = full_ranking_for_range(db, start, end)

    my_rank: int | None = None
    my_total = 0
    top: list[LeaderboardEntry] = []
    for i, (uid, total_seconds) in enumerate(ranking, start=1):
        if uid == user.id:
            my_rank = i
            my_total = total_seconds
        if i <= winner_count:
            u = db.get(User, uid)
            top.append(
                LeaderboardEntry(
                    user_id=uid,
                    display_name=(u.full_name if u and u.full_name else "A student"),
                    total_seconds=total_seconds,
                    rank=i,
                )
            )

    return StudyLeaderboardOut(
        period=period,
        top=top,
        my_rank=my_rank,
        my_total_seconds=my_total,
        winner_count=winner_count,
        reward_days=reward_days,
    )
