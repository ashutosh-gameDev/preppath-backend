import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.db.session import get_db
from app.models.course import Course
from app.models.deck import Deck
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.deck import DeckCreateRequest, DeckOut, DeckPreviewRequest, DeckPreviewResponse, DeckPreviewSummary, DeckUpdate
from app.services import deck_import_service
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/decks", tags=["admin:decks"])

VALID_STATUS = {"draft", "published"}


def _scope_own(q, admin: User):
    """Same ownership rule as admin/questions.py's _scope_own - content
    editors only see/manage decks they created; only super_admin sees all."""
    if admin.role != UserRole.SUPER_ADMIN:
        q = q.where(Deck.created_by == admin.id)
    return q


def _require_owned(deck: Deck | None, admin: User) -> Deck:
    if deck is None or (admin.role != UserRole.SUPER_ADMIN and deck.created_by != admin.id):
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


def _get_course(db: Session, course_id: uuid.UUID) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.get("", response_model=Page[DeckOut])
def list_decks(
    course_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    q = select(Deck)
    if course_id:
        q = q.where(Deck.course_id == course_id)
    if subject_id:
        q = q.where(Deck.subject_id == subject_id)
    if status:
        q = q.where(Deck.status == status)
    q = _scope_own(q, admin)

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    items = db.execute(
        q.order_by(Deck.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return Page.build(items, total, page, page_size)


@router.get("/{deck_id}", response_model=DeckOut)
def get_deck(deck_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    return _require_owned(db.get(Deck, deck_id), admin)


@router.post("/preview", response_model=DeckPreviewResponse)
def preview_deck(payload: DeckPreviewRequest, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    course = _get_course(db, payload.course_id)
    resolved, errors = deck_import_service.validate_deck(payload.raw, course)
    if errors:
        return DeckPreviewResponse(valid=False, errors=errors, deck=None)
    summary = DeckPreviewSummary(
        title=resolved.title, description=resolved.description,
        course_id=resolved.course_id, subject_id=resolved.subject_id,
        topic_id=resolved.topic_id, subtopic_id=resolved.subtopic_id,
        difficulty=resolved.difficulty, theme=resolved.theme,
        estimated_minutes=resolved.estimated_minutes, tags=resolved.tags,
        schema_version=resolved.schema_version, card_count=resolved.card_count,
        block_count=resolved.block_count,
    )
    return DeckPreviewResponse(valid=True, errors=[], deck=summary)


@router.post("", response_model=DeckOut)
def create_deck(payload: DeckCreateRequest, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    course = _get_course(db, payload.course_id)
    resolved, errors = deck_import_service.validate_deck(payload.raw, course)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    deck = Deck(
        title=resolved.title, description=resolved.description,
        course_id=resolved.course_id, subject_id=resolved.subject_id,
        topic_id=resolved.topic_id, subtopic_id=resolved.subtopic_id,
        difficulty=resolved.difficulty, theme=resolved.theme,
        estimated_minutes=resolved.estimated_minutes, tags=resolved.tags,
        schema_version=resolved.schema_version, cards=resolved.cards,
        status="draft", created_by=admin.id,
    )
    db.add(deck)
    db.flush()
    log_action(db, admin.id, "create", "deck", deck.id)
    return deck


@router.patch("/{deck_id}", response_model=DeckOut)
def update_deck(deck_id: uuid.UUID, payload: DeckUpdate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    deck = _require_owned(db.get(Deck, deck_id), admin)
    if payload.status is not None:
        if payload.status not in VALID_STATUS:
            raise HTTPException(status_code=400, detail="status must be one of draft, published")
        deck.status = payload.status
    db.flush()
    log_action(db, admin.id, "update", "deck", deck.id)
    return deck


@router.delete("/{deck_id}", response_model=Message)
def delete_deck(deck_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    deck = _require_owned(db.get(Deck, deck_id), admin)
    db.delete(deck)
    db.flush()
    log_action(db, admin.id, "delete", "deck", deck_id)
    return Message(detail="Deck deleted")
