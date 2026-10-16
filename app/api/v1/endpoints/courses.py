"""Public, read-only course/subject/topic browsing. Admin CRUD lives under /admin/courses."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course, Subject, Topic, TopicProgress
from app.models.custom_topic import CustomTopic
from app.models.user import User
from app.schemas.common import Message
from app.schemas.course import (
    CourseOut,
    CourseTreeOut,
    CustomTopicCreate,
    CustomTopicOut,
    CustomTopicUpdate,
    TopicProgressIn,
    TopicProgressOut,
)

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
        select(TopicProgress.topic_id, TopicProgress.is_completed, TopicProgress.needs_revision)
        .join(Topic, Topic.id == TopicProgress.topic_id)
        .join(Subject, Subject.id == Topic.subject_id)
        .where(TopicProgress.user_id == user.id, Subject.course_id == course_id)
    ).all()
    return [TopicProgressOut(topic_id=r[0], is_completed=r[1], needs_revision=r[2]) for r in rows]


@router.put("/topics/{topic_id}/progress", response_model=Message)
def set_topic_progress(
    topic_id: uuid.UUID, payload: TopicProgressIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Upserts the caller's progress row for this topic. Either field may be
    sent alone (e.g. the Syllabus page's revision toggle only sends
    needs_revision, leaving is_completed untouched) - unset fields keep their
    existing value, or default to a fresh row's normal complete-toggle
    semantics."""
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    existing = db.execute(
        select(TopicProgress).where(TopicProgress.user_id == user.id, TopicProgress.topic_id == topic_id)
    ).scalar_one_or_none()
    if existing is None:
        is_completed = payload.is_completed if payload.is_completed is not None else True
        db.add(
            TopicProgress(
                user_id=user.id,
                topic_id=topic_id,
                is_completed=is_completed,
                completed_at=datetime.now(timezone.utc) if is_completed else None,
                needs_revision=payload.needs_revision or False,
            )
        )
    else:
        if payload.is_completed is not None:
            existing.is_completed = payload.is_completed
            existing.completed_at = datetime.now(timezone.utc) if payload.is_completed else None
        if payload.needs_revision is not None:
            existing.needs_revision = payload.needs_revision
    db.flush()
    return Message(detail="Progress updated")


# --- Custom topics (a student's own syllabus checklist items) -----------------

@router.get("/{course_id}/custom-topics", response_model=list[CustomTopicOut])
def list_custom_topics(course_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every custom topic the caller has added under any subject in this
    course - the Syllabus page merges these into each subject's own topic
    list client-side."""
    return db.execute(
        select(CustomTopic)
        .join(Subject, Subject.id == CustomTopic.subject_id)
        .where(CustomTopic.user_id == user.id, Subject.course_id == course_id)
        .order_by(CustomTopic.order_index, CustomTopic.created_at)
    ).scalars().all()


@router.post("/custom-topics", response_model=CustomTopicOut)
def create_custom_topic(
    payload: CustomTopicCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Give this topic a name")
    next_order = db.execute(
        select(func.coalesce(func.max(CustomTopic.order_index), -1) + 1).where(
            CustomTopic.user_id == user.id, CustomTopic.subject_id == payload.subject_id
        )
    ).scalar_one()
    topic = CustomTopic(user_id=user.id, subject_id=payload.subject_id, name=payload.name.strip(), order_index=next_order)
    db.add(topic)
    db.flush()
    return topic


@router.patch("/custom-topics/{topic_id}", response_model=CustomTopicOut)
def update_custom_topic(
    topic_id: uuid.UUID, payload: CustomTopicUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    topic = db.get(CustomTopic, topic_id)
    if topic is None or topic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Custom topic not found")
    if payload.name is not None:
        topic.name = payload.name.strip() or topic.name
    if payload.is_completed is not None:
        topic.is_completed = payload.is_completed
    db.flush()
    return topic


@router.delete("/custom-topics/{topic_id}", response_model=Message)
def delete_custom_topic(topic_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    topic = db.get(CustomTopic, topic_id)
    if topic is None or topic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Custom topic not found")
    db.delete(topic)
    db.flush()
    return Message(detail="Custom topic deleted")
