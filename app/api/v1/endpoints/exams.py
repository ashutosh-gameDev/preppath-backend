import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.exam import Exam, ExamEvent, UserExamFollow
from app.models.user import User
from app.schemas.common import Message
from app.schemas.exam import ExamDetailOut, ExamOut, ExamWithCountdown

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("", response_model=list[ExamOut])
def list_exams(db: Session = Depends(get_db)) -> list[Exam]:
    return db.execute(select(Exam).where(Exam.is_published.is_(True)).order_by(Exam.name)).scalars().all()


@router.get("/followed", response_model=list[ExamWithCountdown])
def list_followed_exams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    follows = db.execute(select(UserExamFollow).where(UserExamFollow.user_id == user.id)).scalars().all()
    today = date.today()
    results = []
    for f in follows:
        exam = db.get(Exam, f.exam_id)
        if not exam or not exam.is_published:
            continue
        next_event = db.execute(
            select(ExamEvent)
            .where(ExamEvent.exam_id == exam.id, ExamEvent.is_published.is_(True), ExamEvent.event_date >= today)
            .order_by(ExamEvent.event_date.asc())
        ).scalars().first()
        results.append(
            ExamWithCountdown(
                **ExamOut.model_validate(exam).model_dump(),
                next_event=next_event,
                days_remaining=(next_event.event_date - today).days if next_event else None,
                notifications_enabled=f.notifications_enabled,
            )
        )
    results.sort(key=lambda r: (r.days_remaining is None, r.days_remaining))
    return results


@router.get("/{slug}", response_model=ExamDetailOut)
def get_exam(slug: str, user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    exam = db.execute(select(Exam).where(Exam.slug == slug, Exam.is_published.is_(True))).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    events = db.execute(
        select(ExamEvent)
        .where(ExamEvent.exam_id == exam.id, ExamEvent.is_published.is_(True))
        .order_by(ExamEvent.event_date.asc())
    ).scalars().all()
    is_followed = False
    if user:
        is_followed = (
            db.execute(
                select(UserExamFollow).where(UserExamFollow.exam_id == exam.id, UserExamFollow.user_id == user.id)
            ).scalar_one_or_none()
            is not None
        )
    follower_count = db.execute(
        select(UserExamFollow).where(UserExamFollow.exam_id == exam.id)
    ).scalars().all()
    return ExamDetailOut(
        **ExamOut.model_validate(exam).model_dump(),
        events=events,
        is_followed=is_followed,
        follower_count=len(follower_count),
    )


@router.post("/{exam_id}/follow", response_model=Message)
def follow_exam(exam_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    existing = db.execute(
        select(UserExamFollow).where(UserExamFollow.exam_id == exam_id, UserExamFollow.user_id == user.id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(UserExamFollow(exam_id=exam_id, user_id=user.id))
        db.flush()
    return Message(detail="Following exam")


@router.delete("/{exam_id}/follow", response_model=Message)
def unfollow_exam(exam_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(
        select(UserExamFollow).where(UserExamFollow.exam_id == exam_id, UserExamFollow.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        db.flush()
    return Message(detail="Unfollowed exam")
