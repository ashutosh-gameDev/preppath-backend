"""Mistake Book - mostly a read-only view derived from `attempts` (see
services/analytics.latest_wrong_attempts); the one piece of writable state
is dismissing an entry (MistakeDismissal) without re-answering it."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.mistake_dismissal import MistakeDismissal
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.mistakes import MistakeItemOut
from app.schemas.question import QuestionReviewOut
from app.services import analytics

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.get("", response_model=Page[MistakeItemOut])
def list_mistakes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows, total = analytics.latest_wrong_attempts(db, user.id, page, page_size)
    items = [
        MistakeItemOut(
            **QuestionReviewOut.model_validate(question).model_dump(),
            selected_option=attempt.selected_option,
            attempted_at=attempt.attempted_at,
        )
        for attempt, question in rows
    ]
    return Page.build(items, total, page, page_size)


@router.delete("/{question_id}", response_model=Message)
def dismiss_mistake(question_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Clears this question off the Mistake Book without re-answering it -
    reappears automatically if a later attempt on it is wrong again (see
    analytics.latest_wrong_attempts)."""
    existing = db.execute(
        select(MistakeDismissal).where(MistakeDismissal.user_id == user.id, MistakeDismissal.question_id == question_id)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing is None:
        db.add(MistakeDismissal(user_id=user.id, question_id=question_id, dismissed_at=now))
    else:
        existing.dismissed_at = now
    db.flush()
    return Message(detail="Removed from your mistake list")
