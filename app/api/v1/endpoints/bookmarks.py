"""Bookmarks - a student saving a question to revisit later. Toggle-style:
POST is idempotent (bookmarking an already-bookmarked question is a no-op,
not an error), DELETE the same."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.bookmark import QuestionBookmark
from app.models.question import Question
from app.models.user import User
from app.schemas.common import Message
from app.schemas.mistakes import BookmarkedQuestionOut
from app.schemas.question import QuestionReviewOut

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("", response_model=list[BookmarkedQuestionOut])
def list_bookmarks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(QuestionBookmark, Question)
        .join(Question, Question.id == QuestionBookmark.question_id)
        .where(QuestionBookmark.user_id == user.id)
        .order_by(QuestionBookmark.created_at.desc())
    ).all()
    return [
        BookmarkedQuestionOut(
            **QuestionReviewOut.model_validate(question).model_dump(), bookmarked_at=bookmark.created_at
        )
        for bookmark, question in rows
    ]


@router.get("/ids", response_model=list[uuid.UUID])
def list_bookmarked_ids(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Just the question ids - cheap enough to load once and check locally
    (e.g. to show a filled-in bookmark icon) without a request per question."""
    return db.execute(
        select(QuestionBookmark.question_id).where(QuestionBookmark.user_id == user.id)
    ).scalars().all()


@router.post("/{question_id}", response_model=Message)
def add_bookmark(question_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(Question, question_id) is None:
        raise HTTPException(status_code=404, detail="Question not found")
    exists = db.execute(
        select(QuestionBookmark.id).where(QuestionBookmark.user_id == user.id, QuestionBookmark.question_id == question_id)
    ).first()
    if not exists:
        db.add(QuestionBookmark(user_id=user.id, question_id=question_id))
        db.flush()
    return Message(detail="Bookmarked")


@router.delete("/{question_id}", response_model=Message)
def remove_bookmark(question_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bookmark = db.execute(
        select(QuestionBookmark).where(QuestionBookmark.user_id == user.id, QuestionBookmark.question_id == question_id)
    ).scalar_one_or_none()
    if bookmark:
        db.delete(bookmark)
        db.flush()
    return Message(detail="Bookmark removed")
