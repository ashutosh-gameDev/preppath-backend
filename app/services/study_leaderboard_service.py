"""
Study Timer monthly leaderboard: top N students by total study hours in a
calendar month get free Pro, distributed automatically - but lazily, not
via a cron job. `maybe_distribute_rewards` is called at the top of
GET /study-sessions/leaderboard; the first time anyone loads that endpoint
after a month has ended, it computes that month's top N from
`study_sessions` and grants each one Pro via the same `grant_premium` a
paid purchase uses. `leaderboard_rewards` records which (period, rank)
pairs are already paid out, so every later call that same month is a
cheap no-op existence check.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import UserTier
from app.models.study_session import LeaderboardReward, StudySession
from app.models.user import Profile
from app.services import settings_service
from app.services.premium_service import Plan, grant_premium


def _period_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _previous_period(dt: datetime) -> tuple[str, datetime, datetime]:
    """The most recently completed calendar month before `dt`, as
    (period_key, start, end) - end is exclusive."""
    first_of_this_month = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = first_of_this_month
    if first_of_this_month.month == 1:
        start = first_of_this_month.replace(year=first_of_this_month.year - 1, month=12)
    else:
        start = first_of_this_month.replace(month=first_of_this_month.month - 1)
    return _period_key(start), start, end


def current_period(dt: datetime) -> tuple[str, datetime, datetime]:
    """The calendar month `dt` falls in, as (period_key, start, end) - end
    exclusive. Used for the LIVE standings display, as opposed to
    `_previous_period` (used for reward distribution, which only ever pays
    out a month once it's actually over)."""
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return _period_key(start), start, end


def top_n_for_range(db: Session, start: datetime, end: datetime, n: int) -> list[tuple]:
    """[(user_id, total_seconds), ...] ordered by total_seconds desc, for
    study_sessions created in [start, end)."""
    rows = db.execute(
        select(StudySession.user_id, func.sum(StudySession.duration_seconds))
        .where(StudySession.created_at >= start, StudySession.created_at < end)
        .group_by(StudySession.user_id)
        .order_by(func.sum(StudySession.duration_seconds).desc())
        .limit(n)
    ).all()
    return [(row[0], row[1]) for row in rows]


def full_ranking_for_range(db: Session, start: datetime, end: datetime) -> list[tuple]:
    """Every user who logged at least one session in [start, end), ordered
    by total_seconds desc - used for the LIVE leaderboard display (slice
    the top N, find the caller's own rank by position), as opposed to
    `top_n_for_range`'s `.limit(n)` used for reward distribution."""
    rows = db.execute(
        select(StudySession.user_id, func.sum(StudySession.duration_seconds))
        .where(StudySession.created_at >= start, StudySession.created_at < end)
        .group_by(StudySession.user_id)
        .order_by(func.sum(StudySession.duration_seconds).desc())
    ).all()
    return [(row[0], row[1]) for row in rows]


_LAST_DISTRIBUTED_KEY = "study_leaderboard._last_distributed_period"


def maybe_distribute_rewards(db: Session) -> None:
    now = datetime.now(timezone.utc)
    period, start, end = _previous_period(now)
    # Internal bookkeeping (not a tunable, so it's deliberately not in
    # settings_service.DEFAULTS - it never needs to show up in the CRM
    # settings list). Checked first so a month with zero study sessions
    # doesn't re-run the aggregate query on every single request.
    if settings_service.get_setting(db, _LAST_DISTRIBUTED_KEY) == period:
        return

    winner_count = int(settings_service.get_setting(db, "study_leaderboard.winner_count"))
    reward_days = int(settings_service.get_setting(db, "study_leaderboard.reward_days"))
    winners = top_n_for_range(db, start, end, winner_count)

    plan = Plan(key="study_leaderboard", label="Study Leaderboard", amount_paise=0, duration_days=reward_days, tier=UserTier.PRO)
    for rank, (user_id, total_seconds) in enumerate(winners, start=1):
        profile = db.get(Profile, user_id)
        if profile is None:
            continue
        grant_premium(db, profile, plan)
        db.add(LeaderboardReward(period=period, rank_position=rank, user_id=user_id, total_seconds=total_seconds))
    settings_service.set_setting(db, _LAST_DISTRIBUTED_KEY, period)
    db.flush()
