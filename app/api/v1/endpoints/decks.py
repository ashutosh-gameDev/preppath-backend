"""Student-facing "Study Bite" decks: browse published decks for a course,
open one to play through. No enrollment check beyond requiring a logged-in
user - matches practice.py's own `/practice/session`, which likewise filters
by course_id/published status without a separate enrollment gate."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.deck import Deck
from app.models.enums import ContentStatus
from app.models.user import User
from app.schemas.deck import DeckOut

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", response_model=list[DeckOut])
def list_decks(
    course_id: uuid.UUID,
    topic_id: uuid.UUID | None = None,
    subtopic_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(Deck).where(Deck.course_id == course_id, Deck.status == ContentStatus.PUBLISHED)
    if topic_id:
        q = q.where(Deck.topic_id == topic_id)
    if subtopic_id:
        q = q.where(Deck.subtopic_id == subtopic_id)
    return db.execute(q.order_by(Deck.created_at.desc())).scalars().all()


@router.get("/{deck_id}", response_model=DeckOut)
def get_deck(deck_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.get(Deck, deck_id)
    if deck is None or deck.status != ContentStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck
