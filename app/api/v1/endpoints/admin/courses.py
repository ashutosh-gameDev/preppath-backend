import uuid

from fastapi import APIRouter, Depends, HTTPException
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_admin, require_content_access
from app.db.session import get_db
from app.models.course import Course, Subject, Topic
from app.models.user import User
from app.schemas.common import Message
from app.schemas.course import (
    CourseCreate,
    CourseTreeOut,
    CourseUpdate,
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
    TopicCreate,
    TopicOut,
    TopicUpdate,
)
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/courses", tags=["admin:courses"])


def _unique_slug(db: Session, model, name: str, exclude_id: uuid.UUID | None = None, scope_filter=None) -> str:
    base = slugify(name)
    slug = base
    i = 1
    while True:
        q = select(model).where(model.slug == slug)
        if exclude_id:
            q = q.where(model.id != exclude_id)
        if scope_filter is not None:
            q = q.where(scope_filter)
        if db.execute(q).scalar_one_or_none() is None:
            return slug
        i += 1
        slug = f"{base}-{i}"


@router.get("", response_model=list[CourseTreeOut])
def list_courses(admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    # GET is intentionally on require_content_access (not require_admin):
    # content_editor accounts need to read the tree to tag questions to a
    # course/subject/topic, even though they can't create/edit/delete it.
    return db.execute(
        select(Course).options(selectinload(Course.subjects).selectinload(Subject.topics)).order_by(Course.name)
    ).scalars().all()


@router.post("", response_model=CourseTreeOut)
def create_course(payload: CourseCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    slug = _unique_slug(db, Course, payload.name)
    course = Course(**payload.model_dump(), slug=slug)
    db.add(course)
    db.flush()
    log_action(db, admin.id, "create", "course", course.id)
    return course


@router.patch("/{course_id}", response_model=CourseTreeOut)
def update_course(course_id: uuid.UUID, payload: CourseUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value:
            course.slug = _unique_slug(db, Course, value, exclude_id=course.id)
        setattr(course, field, value)
    db.flush()
    log_action(db, admin.id, "update", "course", course.id)
    return course


@router.delete("/{course_id}", response_model=Message)
def delete_course(course_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    try:
        db.delete(course)
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cannot delete a course that has questions/tests referencing it")
    log_action(db, admin.id, "delete", "course", course_id)
    return Message(detail="Course deleted")


# --- Subjects -----------------------------------------------------------------

@router.post("/{course_id}/subjects", response_model=SubjectOut)
def create_subject(course_id: uuid.UUID, payload: SubjectCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    slug = _unique_slug(db, Subject, payload.name, scope_filter=Subject.course_id == course_id)
    subject = Subject(**payload.model_dump(), course_id=course_id, slug=slug)
    db.add(subject)
    db.flush()
    log_action(db, admin.id, "create", "subject", subject.id)
    return subject


@router.patch("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: uuid.UUID, payload: SubjectUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value:
            subject.slug = _unique_slug(db, Subject, value, exclude_id=subject.id, scope_filter=Subject.course_id == subject.course_id)
        setattr(subject, field, value)
    db.flush()
    log_action(db, admin.id, "update", "subject", subject.id)
    return subject


@router.delete("/subjects/{subject_id}", response_model=Message)
def delete_subject(subject_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    try:
        db.delete(subject)
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cannot delete a subject that has questions/tests referencing it")
    log_action(db, admin.id, "delete", "subject", subject_id)
    return Message(detail="Subject deleted")


# --- Topics ---------------------------------------------------------------------

@router.post("/subjects/{subject_id}/topics", response_model=TopicOut)
def create_topic(subject_id: uuid.UUID, payload: TopicCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    slug = _unique_slug(db, Topic, payload.name, scope_filter=Topic.subject_id == subject_id)
    topic = Topic(**payload.model_dump(), subject_id=subject_id, slug=slug)
    db.add(topic)
    db.flush()
    log_action(db, admin.id, "create", "topic", topic.id)
    return topic


@router.patch("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: uuid.UUID, payload: TopicUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value:
            topic.slug = _unique_slug(db, Topic, value, exclude_id=topic.id, scope_filter=Topic.subject_id == topic.subject_id)
        setattr(topic, field, value)
    db.flush()
    log_action(db, admin.id, "update", "topic", topic.id)
    return topic


@router.delete("/topics/{topic_id}", response_model=Message)
def delete_topic(topic_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    try:
        db.delete(topic)
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cannot delete a topic that has questions referencing it")
    log_action(db, admin.id, "delete", "topic", topic_id)
    return Message(detail="Topic deleted")
