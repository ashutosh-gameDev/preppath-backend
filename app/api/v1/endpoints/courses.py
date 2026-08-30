"""Public, read-only course/subject/topic browsing. Admin CRUD lives under /admin/courses."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course, Subject, Topic, TopicProgress
from app.models.user import User
from app.schemas.common import Message
from app.schemas.course import CourseOut, CourseTreeOut, TopicProgressIn, TopicProgressOut

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return db.execute(select(Course).where(Course.is_published.is_(True)).order_by(Course.name)).scalars().all()


@router.get("/{slug}", response_model=CourseTreeOut)
def get_course_tree(slug: str, db: Session = Depends(get_db)) -> Course:
    course = db.execute(
        select(Course)
        .options(selectinload(Course.subjects).selectinload(Subject.topics))
        .where(Course.slug == slug, Course.is_published.is_(True))
    ).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    course.subjects = [s for s in course.subjects if s.is_published]
    for s in course.subjects:
        s.topics = [t for t in s.topics if t.is_published]
    return course


# --- Syllabus progress (mark topic complete/incomplete) -----------------------

@router.get("/{course_id}/progress", response_model=list[TopicProgressOut])
def get_course_progress(course_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Which topics in this course the student has marked complete - merged
    client-side onto the course tree from `/courses/{slug}` (kept separate so
    the tree endpoint stays public/cacheable and per-user state doesn't leak
    into it)."""
    rows = db.execute(
        select(TopicProgress.topic_id, TopicProgress.is_completed)
        .join(Topic, Topic.id == TopicProgress.topic_id)
        .join(Subject, Subject.id == Topic.subject_id)
        .where(TopicProgress.user_id == user.id, Subject.course_id == course_id)
    ).all()
    return [TopicProgressOut(topic_id=r[0], is_completed=r[1]) for r in rows]


@router.put("/topics/{topic_id}/progress", response_model=Message)
def set_topic_progress(
    topic_id: uuid.UUID, payload: TopicProgressIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    existing = db.execute(
        select(TopicProgress).where(TopicProgress.user_id == user.id, TopicProgress.topic_id == topic_id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            TopicProgress(
                user_id=user.id,
                topic_id=topic_id,
                is_completed=payload.is_completed,
                completed_at=datetime.now(timezone.utc) if payload.is_completed else None,
            )
        )
    else:
        existing.is_completed = payload.is_completed
        existing.completed_at = datetime.now(timezone.utc) if payload.is_completed else None
    db.flush()
    return Message(detail="Progress updated")
