"""
Configurable platform settings (scoring weights, analytics thresholds,
recommendation rules...) with hardcoded fallbacks. An admin can override any
key by writing a row to `platform_settings`; nothing else in the codebase
should hardcode a tunable number - it should call `get_setting` instead so
the whole scoring/analytics/leaderboard architecture stays configurable
without a redeploy, per the product brief.
"""
from typing import Any

from sqlalchemy.orm import Session

from app.models.admin import PlatformSetting

DEFAULTS: dict[str, Any] = {
    # XP awarded per correctly answered question, by difficulty.
    "xp.correct.easy": 5,
    "xp.correct.medium": 10,
    "xp.correct.hard": 15,
    # Small participation XP for attempting even if wrong - keeps practice
    # worthwhile without making raw volume the dominant leaderboard signal
    # (wrong answers earn a fraction of a correct answer at the same
    # difficulty).
    "xp.attempt.participation": 1,
    # Bonus XP on completing a full test, scaled by the % score achieved -
    # rewards accuracy over merely finishing.
    "xp.test.completion_base": 20,
    "xp.test.completion_per_pct": 0.5,
    "xp.daily_challenge.bonus": 25,
    # Streak bonus XP = min(streak_days, cap) * per_day
    "xp.streak.per_day": 2,
    "xp.streak.cap_days": 30,
    # Analytics: don't call something a strength/weakness on too few attempts.
    "analytics.min_attempts_for_signal": 5,
    "analytics.strong_threshold_pct": 80,
    "analytics.weak_threshold_pct": 70,
    # Recommendation: a topic not touched in this many days is "stale".
    "recommendation.stale_days": 14,
    "recommendation.weak_practice_count": 20,
    "recommendation.stale_practice_count": 10,
    "recommendation.challenge_count": 15,
    "recommendation.challenge_accuracy_threshold": 85,
    # Leaderboard: minimum questions attempted (all-time) to appear ranked -
    # prevents a single lucky question from placing someone at rank #1.
    "leaderboard.min_attempts": 10,
    # Daily challenge default size.
    "daily_challenge.question_count": 10,
    "daily_challenge.seconds_per_question": 45,
}


def get_setting(db: Session, key: str) -> Any:
    row = db.get(PlatformSetting, key)
    if row is not None:
        return row.value.get("v", DEFAULTS.get(key))
    return DEFAULTS.get(key)


def get_settings_bulk(db: Session, keys: list[str]) -> dict[str, Any]:
    return {k: get_setting(db, k) for k in keys}


def set_setting(db: Session, key: str, value: Any, description: str | None = None) -> PlatformSetting:
    row = db.get(PlatformSetting, key)
    if row is None:
        row = PlatformSetting(key=key, value={"v": value}, description=description)
        db.add(row)
    else:
        row.value = {"v": value}
        if description:
            row.description = description
    db.flush()
    return row
