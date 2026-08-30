"""
Super-admin-only management of content-editor (intern) accounts: create a
username/password login that can manage questions and tests/PYQ papers only
(see api/deps.require_content_access) - never users, settings, courses, or
exam notifications.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_super_admin
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import Profile, User
from app.schemas.common import Message
from app.schemas.team import TeamMemberCreate, TeamMemberOut, TeamMemberPasswordReset
from app.services import team_service
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/team", tags=["admin:team"])


@router.get("", response_model=list[TeamMemberOut])
def list_team(admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return db.execute(
        select(User).where(User.role == UserRole.CONTENT_EDITOR).order_by(User.created_at.desc())
    ).scalars().all()


@router.post("", response_model=TeamMemberOut)
def create_team_member(payload: TeamMemberCreate, admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' is already taken")

    auth_user_id = team_service.create_intern_auth_user(payload.username, payload.password)

    user = User(
        id=uuid.UUID(auth_user_id),
        email=team_service.username_to_email(payload.username),
        username=payload.username,
        role=UserRole.CONTENT_EDITOR,
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.flush()
    log_action(db, admin.id, "create", "team_member", user.id, {"username": payload.username})
    return user


@router.patch("/{user_id}/password", response_model=Message)
def reset_team_member_password(
    user_id: uuid.UUID, payload: TeamMemberPasswordReset, admin: User = Depends(require_super_admin), db: Session = Depends(get_db)
):
    member = db.get(User, user_id)
    if member is None or member.role != UserRole.CONTENT_EDITOR:
        raise HTTPException(status_code=404, detail="Team member not found")
    team_service.reset_intern_password(str(member.id), payload.password)
    log_action(db, admin.id, "reset_password", "team_member", member.id)
    return Message(detail="Password updated")


@router.patch("/{user_id}/deactivate", response_model=Message)
def toggle_team_member_active(
    user_id: uuid.UUID, is_active: bool, admin: User = Depends(require_super_admin), db: Session = Depends(get_db)
):
    """Toggling is_active is the actual access gate (enforced in
    get_current_user) - immediate and doesn't depend on Supabase being
    reachable, unlike deleting the auth user."""
    member = db.get(User, user_id)
    if member is None or member.role != UserRole.CONTENT_EDITOR:
        raise HTTPException(status_code=404, detail="Team member not found")
    member.is_active = is_active
    db.flush()
    log_action(db, admin.id, "deactivate" if not is_active else "reactivate", "team_member", member.id)
    return Message(detail="Team member updated")


@router.delete("/{user_id}", response_model=Message)
def delete_team_member(user_id: uuid.UUID, admin: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    member = db.get(User, user_id)
    if member is None or member.role != UserRole.CONTENT_EDITOR:
        raise HTTPException(status_code=404, detail="Team member not found")
    team_service.delete_intern_auth_user(str(member.id))
    db.delete(member)
    db.flush()
    log_action(db, admin.id, "delete", "team_member", user_id)
    return Message(detail="Team member removed")
