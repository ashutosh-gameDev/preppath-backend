"""
Deterministic achievement evaluation. Call `check_and_award` after any event
that could unlock one (answering a question, finishing a test, streak
update). Cheap: it only reads the already-updated `Profile` counters, no
extra aggregation queries, except for the rank-based achievement.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import AchievementCriteria, XPReason
from app.models.gamification import Achievement, UserAchievement
from app.models.user import Profile
from app.services.xp_service import award_xp


def _current_value(db: Session, profile: Profile, criteria_type: str) -> int | None:
    if criteria_type == AchievementCriteria.QUESTIONS_ATTEMPTED:
        return profile.questions_attempted
    if criteria_type == AchievementCriteria.TESTS_COMPLETED:
        return profile.tests_completed
    if criteria_type == AchievementCriteria.PYQ_COMPLETED:
        return profile.pyqs_completed
    if criteria_type == AchievementCriteria.STREAK_DAYS:
        return profile.current_streak
    if criteria_type == AchievementCriteria.FIRST_TEST:
        return 1 if profile.tests_completed >= 1 else 0
    if criteria_type == AchievementCriteria.ACCURACY_PCT:
        if profile.questions_attempted < 20:  # need a meaningful sample
            return None
        return round(100 * profile.questions_correct / profile.questions_attempted)
    if criteria_type == AchievementCriteria.GLOBAL_RANK_TOP_N:
        from app.services.leaderboard_service import global_rank
        from app.services.settings_service import get_setting

        min_attempts = int(get_setting(db, "leaderboard.min_attempts") or 10)
        rank = global_rank(db, profile.user_id, min_attempts)
        return None if rank is None else rank
    return None


def check_and_award(db: Session, profile: Profile) -> list[Achievement]:
    already_earned_ids = {
        row[0]
        for row in db.execute(
            select(UserAchievement.achievement_id).where(UserAchievement.user_id == profile.user_id)
        ).all()
    }
    newly_earned: list[Achievement] = []

    for achievement in db.execute(select(Achievement)).scalars().all():
        if achievement.id in already_earned_ids:
            continue
        current = _current_value(db, profile, achievement.criteria_type)
        if current is None:
            continue

        unlocked = (
            current <= achievement.criteria_value
            if achievement.criteria_type == AchievementCriteria.GLOBAL_RANK_TOP_N
            else current >= achievement.criteria_value
        )
        if unlocked:
            db.add(UserAchievement(user_id=profile.user_id, achievement_id=achievement.id))
            if achievement.xp_reward:
                award_xp(db, profile, achievement.xp_reward, XPReason.ACHIEVEMENT, "achievement", achievement.id)
            newly_earned.append(achievement)

    if newly_earned:
        db.flush()
    return newly_earned
