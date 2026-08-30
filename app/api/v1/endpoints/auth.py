"""
There is no login/signup/token endpoint here on purpose - Supabase Auth
handles credential storage, signup, login, password reset and token issuance
directly from the frontend (student-web / admin-web talk to Supabase
directly for those flows). This backend only ever verifies the resulting
JWT (see `core/security.py`) and lazily provisions a matching `users` row on
first sight (see `api/deps.get_current_user`). `/auth/me` is a convenience
endpoint for the frontend to confirm the token is valid and fetch the
resolved local user + profile in one call right after login.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import Profile, User
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    user.profile = db.get(Profile, user.id)
    return user
