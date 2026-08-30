"""
XP ledger writes + the cached Profile counters that ride along with them.
Every code path that grants XP goes through `award_xp` so the ledger
(`xp_transactions`) and the cache (`profiles.xp_total`) never drift apart.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.enums import XPReason
from app.models.gamification import XPTransaction
from app.models.user import Profile
from app.services.settings_service import get_setting

# Simple level curve: level N requires N * 100 cumulative XP more than the
# last (100, 300, 600, 1000, ...). Deliberately simple/tunable - swap for a
# smarter curve later without touching callers.
def xp_to_level(xp_total: int) -> int:
    level = 1
    threshold = 0
    step = 100
    while xp_total >= threshold + step:
        threshold += step
        step += 100
        level += 1
    return level


def award_xp(
    db: Session,
    profile: Profile,
    amount: int,
    reason: str,
    ref_type: str | None = None,
    ref_id: uuid.UUID | None = None,
) -> int:
    if amount == 0:
        return profile.xp_total
    db.add(
        XPTransaction(
            user_id=profile.user_id,
            amount=amount,
            reason=reason,
            ref_type=ref_type,
            ref_id=ref_id,
        )
    )
    profile.xp_total = max(0, profile.xp_total + amount)
    profile.level = xp_to_level(profile.xp_total)
    db.flush()
    return profile.xp_total


def xp_for_correct_answer(db: Session, difficulty: str) -> int:
    return int(get_setting(db, f"xp.correct.{difficulty}") or 0)


def touch_daily_activity(db: Session, profile: Profile) -> None:
    """
    Update streak counters. Called once per day the student engages with any
    practice/test activity. Idempotent within a day.
    """
    today = datetime.now(timezone.utc).date()
    last = profile.last_activity_date

    if last == today:
        return  # already counted today

    if last == today - timedelta(days=1):
        profile.current_streak += 1
    else:
        profile.current_streak = 1

    profile.longest_streak = max(profile.longest_streak, profile.current_streak)
    profile.last_activity_date = today

    bonus_per_day = int(get_setting(db, "xp.streak.per_day") or 0)
    cap_days = int(get_setting(db, "xp.streak.cap_days") or 0)
    bonus = min(profile.current_streak, cap_days) * bonus_per_day
    if bonus > 0:
        award_xp(db, profile, bonus, XPReason.STREAK_BONUS)

    db.flush()
