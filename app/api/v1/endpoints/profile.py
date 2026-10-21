from fastapi import APIRouter, Depends
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.attempt import Attempt
from app.models.course import SubtopicProgress, TopicProgress
from app.models.custom_topic import CustomTopic
from app.models.gamification import Achievement, UserAchievement, XPTransaction
from app.models.mistake_dismissal import MistakeDismissal
from app.models.study_session import StudySession
from app.models.test import TestAttempt
from app.models.user import Profile, User
from app.models.video_watch import VideoWatch
from app.schemas.common import Message
from app.schemas.gamification import AchievementOut
from app.services import leaderboard_service
from app.services.settings_service import get_setting

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me")
def get_my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(Profile, user.id)
    min_attempts = int(get_setting(db, "leaderboard.min_attempts") or 10)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at,
        },
        "profile": profile,
        "global_rank": leaderboard_service.global_rank(db, user.id, min_attempts),
        "accuracy": round(100 * profile.questions_correct / profile.questions_attempted, 1)
        if profile.questions_attempted
        else 0.0,
    }


@router.post("/reset-progress", response_model=Message)
def reset_my_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A student starting over from scratch. Permanently deletes every
    practice/performance record this account has ever produced - the one
    deliberate exception to "attempts/xp_transactions/study_sessions are
    append-only, nothing is ever deleted" elsewhere in this codebase.

    Explicitly NOT touched: the user account itself, course enrollments
    (and target_exam_date), premium tier/payments, job-eligibility profile
    fields (date_of_birth/qualification/city/state/gender/category),
    question bookmarks, reminders, notes, and leaderboard_rewards (a
    historical record of payouts already made, not this student's own
    editable state).
    """
    db.execute(delete(Attempt).where(Attempt.user_id == user.id))
    db.execute(delete(TestAttempt).where(TestAttempt.user_id == user.id))
    db.execute(delete(TopicProgress).where(TopicProgress.user_id == user.id))
    db.execute(delete(SubtopicProgress).where(SubtopicProgress.user_id == user.id))
    db.execute(delete(XPTransaction).where(XPTransaction.user_id == user.id))
    db.execute(delete(UserAchievement).where(UserAchievement.user_id == user.id))
    db.execute(delete(MistakeDismissal).where(MistakeDismissal.user_id == user.id))
    db.execute(delete(StudySession).where(StudySession.user_id == user.id))
    db.execute(delete(VideoWatch).where(VideoWatch.user_id == user.id))
    db.execute(update(CustomTopic).where(CustomTopic.user_id == user.id).values(is_completed=False))

    profile = db.get(Profile, user.id)
    if profile is not None:
        profile.xp_total = 0
        profile.level = 1
        profile.current_streak = 0
        profile.longest_streak = 0
        profile.last_activity_date = None
        profile.questions_attempted = 0
        profile.questions_correct = 0
        profile.tests_completed = 0
        profile.pyqs_completed = 0

    db.flush()
    return Message(detail="Progress reset")


@router.get("/achievements", response_model=list[AchievementOut])
def get_my_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(Profile, user.id)
    earned = {
        row.achievement_id: row.earned_at
        for row in db.execute(select(UserAchievement).where(UserAchievement.user_id == user.id)).scalars().all()
    }

    from app.services.achievements_service import _current_value

    out = []
    for a in db.execute(select(Achievement)).scalars().all():
        current = _current_value(db, profile, a.criteria_type) or 0
        out.append(
            AchievementOut(
                id=a.id,
                code=a.code,
                name=a.name,
                description=a.description,
                icon=a.icon,
                xp_reward=a.xp_reward,
                earned=a.id in earned,
                earned_at=earned.get(a.id),
                progress_current=min(current, a.criteria_value),
                progress_target=a.criteria_value,
            )
        )
    return out
