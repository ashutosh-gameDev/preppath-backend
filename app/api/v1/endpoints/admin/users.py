"""
Admin user management. Deliberately does NOT expose any endpoint to change a
user's password/email/auth credentials - those are owned by Supabase Auth.
Admins can only view stats and enable/disable an account (blocks API access
via `User.is_active`, checked in `api/deps.get_current_user`).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import Profile, User
from app.schemas.common import Page
from app.schemas.user import AdminUserListItem, AdminUserStatusUpdate, UserOut

router = APIRouter(prefix="/admin/users", tags=["admin:users"])


@router.get("", response_model=Page[AdminUserListItem])
def list_users(
    search: str | None = None,
    role: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = select(User, Profile).join(Profile, Profile.user_id == User.id)
    if search:
        q = q.where(User.email.ilike(f"%{search}%"))
    if role:
        q = q.where(User.role == role)

    all_rows = db.execute(q.order_by(User.created_at.desc())).all()
    total = len(all_rows)
    page_rows = all_rows[(page - 1) * page_size : (page - 1) * page_size + page_size]

    items = [
        AdminUserListItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            last_active_at=u.last_active_at,
            xp_total=p.xp_total,
            questions_attempted=p.questions_attempted,
            accuracy=round(100 * p.questions_correct / p.questions_attempted, 1) if p.questions_attempted else 0.0,
            tests_completed=p.tests_completed,
        )
        for u, p in page_rows
    ]
    return Page.build(items, total, page, page_size)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.profile = db.get(Profile, user.id)
    return user


@router.patch("/{user_id}/status", response_model=UserOut)
def set_user_status(user_id: uuid.UUID, payload: AdminUserStatusUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = payload.is_active
    db.flush()
    user.profile = db.get(Profile, user.id)
    return user
