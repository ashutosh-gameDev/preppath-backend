"""
Local-development-only sign-in shortcut.

No real Supabase project is required to click through the app locally: this
mints a Supabase-session-shaped JWT (signed with APP_SECRET_KEY, which
`decode_supabase_token` also tries first whenever ENVIRONMENT=development)
for an existing seeded user, so the frontend can store it exactly like a
real Supabase session and every authenticated route works normally.

Hard-disabled unless ENVIRONMENT=development (checked per-request, not just
at import time, so a config change takes effect without a code change) -
this must never be reachable in a deployed environment, since it would let
anyone sign in as anyone with just their email.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/dev", tags=["dev-only"])


def _require_dev_mode() -> None:
    if settings.ENVIRONMENT.lower() != "development":
        raise HTTPException(status_code=404, detail="Not found")


class DevUserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str


class DevLoginRequest(BaseModel):
    email: str


class DevLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: uuid.UUID
    email: str
    full_name: str | None
    role: str


@router.get("/users", response_model=list[DevUserOut])
def list_dev_users(db: Session = Depends(get_db)):
    _require_dev_mode()
    users = db.execute(select(User).where(User.is_active.is_(True)).order_by(User.role.desc(), User.email)).scalars().all()
    return users


@router.post("/login", response_model=DevLoginResponse)
def dev_login(payload: DevLoginRequest, db: Session = Depends(get_db)):
    _require_dev_mode()
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="No user with that email - seed the database first")

    now = datetime.now(timezone.utc)
    expires_in = 21600  # 6 hours
    token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "aud": "authenticated",
            "role": "authenticated",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        },
        settings.APP_SECRET_KEY,
        algorithm="HS256",
    )

    return DevLoginResponse(
        access_token=token,
        refresh_token="dev-mode-fake-refresh-token",
        expires_in=expires_in,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )
