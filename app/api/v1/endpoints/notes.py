"""
Notes Board sync - Premium tier only. Normal/Pro students use the Notes
Board entirely client-side (IndexedDB, see student-web lib/notes-db.ts) and
never call this at all; these endpoints exist purely to mirror a Premium
student's categories/pages so they're available on another device. Every
route 403s for a non-Premium caller rather than silently no-opping, so the
frontend can surface a clear "upgrade to sync" message instead of a
mysteriously-not-syncing feature.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_profile, get_current_user
from app.db.session import get_db
from app.models.notes import NoteCategory, NotePage
from app.models.user import Profile, User
from app.schemas.common import Message
from app.schemas.notes import NoteCategoryIn, NoteCategoryOut, NotePageIn, NotePageMetaOut, NotePageOut
from app.services.premium_service import is_premium

router = APIRouter(prefix="/notes", tags=["notes"])


def _require_premium(profile: Profile) -> None:
    if not is_premium(profile):
        raise HTTPException(status_code=403, detail="Notes sync is a Premium feature - your notes still work offline on this device.")


@router.get("/categories", response_model=list[NoteCategoryOut])
def list_categories(
    user: User = Depends(get_current_user), profile: Profile = Depends(get_current_active_profile), db: Session = Depends(get_db)
):
    _require_premium(profile)
    return db.execute(select(NoteCategory).where(NoteCategory.user_id == user.id).order_by(NoteCategory.name)).scalars().all()


@router.put("/categories/{category_id}", response_model=NoteCategoryOut)
def upsert_category(
    category_id: uuid.UUID,
    payload: NoteCategoryIn,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    _require_premium(profile)
    category = db.get(NoteCategory, category_id)
    if category is None:
        category = NoteCategory(id=category_id, user_id=user.id, name=payload.name, color=payload.color)
        db.add(category)
    else:
        if category.user_id != user.id:
            raise HTTPException(status_code=404, detail="Category not found")
        category.name = payload.name
        category.color = payload.color
    db.flush()
    return category


@router.delete("/categories/{category_id}", response_model=Message)
def delete_category(
    category_id: uuid.UUID,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    _require_premium(profile)
    category = db.get(NoteCategory, category_id)
    if category is None or category.user_id != user.id:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.flush()
    return Message(detail="Category deleted")


@router.get("/pages", response_model=list[NotePageMetaOut])
def list_pages(
    category_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    _require_premium(profile)
    q = select(NotePage).where(NotePage.user_id == user.id)
    if category_id:
        q = q.where(NotePage.category_id == category_id)
    return db.execute(q.order_by(NotePage.updated_at.desc())).scalars().all()


@router.get("/pages/{page_id}", response_model=NotePageOut)
def get_page(
    page_id: uuid.UUID,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    _require_premium(profile)
    page = db.get(NotePage, page_id)
    if page is None or page.user_id != user.id:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.put("/pages/{page_id}", response_model=NotePageOut)
def upsert_page(
    page_id: uuid.UUID,
    payload: NotePageIn,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    """Upsert keyed on the client-generated id - a page created offline
    syncs here the first time Premium access is confirmed, and every save
    after that just overwrites (last-write-wins, no merge)."""
    _require_premium(profile)
    page = db.get(NotePage, page_id)
    if page is None:
        page = NotePage(
            id=page_id, user_id=user.id, category_id=payload.category_id,
            title=payload.title, background=payload.background, canvas_json=payload.canvas_json,
        )
        db.add(page)
    else:
        if page.user_id != user.id:
            raise HTTPException(status_code=404, detail="Page not found")
        page.category_id = payload.category_id
        page.title = payload.title
        page.background = payload.background
        page.canvas_json = payload.canvas_json
    db.flush()
    return page


@router.delete("/pages/{page_id}", response_model=Message)
def delete_page(
    page_id: uuid.UUID,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    _require_premium(profile)
    page = db.get(NotePage, page_id)
    if page is None or page.user_id != user.id:
        raise HTTPException(status_code=404, detail="Page not found")
    db.delete(page)
    db.flush()
    return Message(detail="Page deleted")
