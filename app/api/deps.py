"""
Shared FastAPI dependencies: DB session, current user resolution, and role
guards. Every protected route depends on `get_current_user` (or one of the
role-restricted wrappers below) - none of them ever trust a role/user id
passed in the request body or query string.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_supabase_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import Profile, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token_payload = decode_supabase_token(credentials.credentials)
    user_id = uuid.UUID(token_payload.sub)

    user = db.get(User, user_id)
    if user is None:
        # First time we see this Supabase auth user - provision the local
        # row + profile. Role always defaults to `student`; an admin can only
        # ever be promoted via a trusted server-side action (seed script /
        # direct DB update / another admin's endpoint), never via signup.
        user = User(
            id=user_id,
            email=token_payload.email or f"{user_id}@unknown.local",
            role=UserRole.STUDENT,
        )
        db.add(user)
        db.flush()
        db.add(Profile(user_id=user.id))
        db.flush()

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Cheap last-seen tracking, throttled to once every few minutes so it
    # doesn't turn every request into a write.
    now = datetime.now(timezone.utc)
    if user.last_active_at is None or now - user.last_active_at > timedelta(minutes=5):
        user.last_active_at = now
        db.flush()

    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Same resolution as `get_current_user` but returns None instead of 401
    when no/invalid credentials are supplied - for public endpoints whose
    response shape changes slightly for a logged-in caller (e.g. 'is this
    exam followed by me')."""
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def get_current_active_profile(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Profile:
    profile = db.get(Profile, user.id)
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()
    return profile


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_content_access(user: User = Depends(get_current_user)) -> User:
    """Questions/tests/PYQ-paper management - deliberately wider than
    require_admin so content_editor (intern) accounts can upload/edit content,
    but every other admin route (users, settings, courses, exam notifications)
    stays on require_admin/require_super_admin."""
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.CONTENT_EDITOR):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Content access required")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return user
