from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.gamification import Achievement, UserAchievement
from app.models.user import Profile, User
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
