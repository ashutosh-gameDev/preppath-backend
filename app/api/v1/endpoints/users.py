from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import Profile, User
from app.schemas.user import UserOut, UserUpdateMe

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_my_user(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    user.profile = db.get(Profile, user.id)
    return user


@router.patch("/me", response_model=UserOut)
def update_my_user(
    payload: UserUpdateMe, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url

    profile = db.get(Profile, user.id)
    if profile and payload.daily_goal_questions is not None:
        profile.daily_goal_questions = payload.daily_goal_questions

    db.flush()
    user.profile = profile
    return user
