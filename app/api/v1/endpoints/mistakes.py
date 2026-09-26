"""Mistake Book - read-only view derived from `attempts` (see
services/analytics.latest_wrong_attempts). No new attempt data is written
here; this just surfaces what's already recorded."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
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
