import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_admin, require_content_access
from app.db.session import get_db
from app.models.course import Course, Subject, Subtopic, Topic
from app.models.question import Question
from app.models.user import User
from app.schemas.common import Message
from app.schemas.course import (
    BulkCourseImportRequest,
    BulkCourseImportResult,
    CourseCreate,
    CourseTreeOut,
    CourseUpdate,
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
    SubtopicCreate,
    SubtopicOut,
    SubtopicUpdate,
    TopicCreate,
    TopicOut,
    TopicUpdate,
)
from app.services import course_import_service
from app.services.admin_log_service import log_action
from app.services.course_service import publish_course_tree, unique_slug as _unique_slug

router = APIRouter(prefix="/admin/courses", tags=["admin:courses"])


@router.get("", response_model=list[CourseTreeOut])
def list_courses(admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    # GET is intentionally on require_content_access (not require_admin):
    # content_editor accounts need to read the tree to tag questions to a
    # course/subject/topic, even though they can't create/edit/delete it.
    return db.execute(
        select(Course)
        .options(selectinload(Course.subjects).selectinload(Subject.topics).selectinload(Topic.subtopics))
        .order_by(Course.name)
    ).scalars().all()


@router.post("", response_model=CourseTreeOut)
def create_course(payload: CourseCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    slug = _unique_slug(db, Course, payload.name)
    course = Course(**payload.model_dump(), slug=slug)
    db.add(course)
    db.flush()
    log_action(db, admin.id, "create", "course", course.id)
    return course


@router.post("/bulk-import", response_model=BulkCourseImportResult)
def bulk_import_courses(payload: BulkCourseImportRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Creates a whole course -> subjects -> topics structure from one JSON
    document instead of the one-at-a-time admin UI - the natural shape for
    AI-generated syllabus content. Idempotent by name (case-insensitive):
    re-importing the same or an extended document only adds what's missing,
    so it's safe to generate more content later and re-upload."""
    result = course_import_service.import_courses(db, payload)
    log_action(
        db, admin.id, "bulk_import", "course",
        extra={
            "courses_created": result.courses_created,
            "subjects_created": result.subjects_created,
            "topics_created": result.topics_created,
        },
    )
    return result


@router.patch("/{course_id}", response_model=CourseTreeOut)
def update_course(course_id: uuid.UUID, payload: CourseUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    was_published = course.is_published
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value:
            course.slug = _unique_slug(db, Course, value, exclude_id=course.id)
        setattr(course, field, value)
    db.flush()
    extra = None
    if course.is_published and not was_published:
        # Publishing a course publishes its whole syllabus (subjects, chapters,
        # subtopics). Only the draft -> published switch does this, so saving an
        # already-published course never re-publishes items deliberately kept as drafts.
        extra = {"published_children": publish_course_tree(db, course.id)}
        db.refresh(course)
    log_action(db, admin.id, "update", "course", course.id, extra)
    return course


@router.delete("/{course_id}", response_model=Message)
def delete_course(course_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    question_count = db.execute(select(func.count(Question.id)).where(Question.course_id == course_id)).scalar_one()
    if question_count:
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{course.name}' still has {question_count} question(s). Deleting the course would permanently "
                "delete them too - move them to another course or delete them from the Questions page first."
            ),
        )
    try:
        db.delete(course)
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cannot delete a course that still has questions referencing it")
    log_action(db, admin.id, "delete", "course", course_id, {"name": course.name})
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
    question_count = db.execute(select(func.count(Question.id)).where(Question.subject_id == subject_id)).scalar_one()
    if question_count:
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{subject.name}' still has {question_count} question(s). Deleting the subject would permanently "
                "delete them too - move them to another subject or delete them from the Questions page first."
            ),
        )
    try:
        db.delete(subject)
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Cannot delete a subject that still has questions referencing it")
    log_action(db, admin.id, "delete", "subject", subject_id, {"name": subject.name})
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


# --- Subtopics -------------------------------------------------------------------

@router.post("/topics/{topic_id}/subtopics", response_model=SubtopicOut)
def create_subtopic(topic_id: uuid.UUID, payload: SubtopicCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    slug = _unique_slug(db, Subtopic, payload.name, scope_filter=Subtopic.topic_id == topic_id)
    subtopic = Subtopic(**payload.model_dump(), topic_id=topic_id, slug=slug)
    db.add(subtopic)
    db.flush()
    log_action(db, admin.id, "create", "subtopic", subtopic.id)
    return subtopic


@router.patch("/subtopics/{subtopic_id}", response_model=SubtopicOut)
def update_subtopic(subtopic_id: uuid.UUID, payload: SubtopicUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    subtopic = db.get(Subtopic, subtopic_id)
    if subtopic is None:
        raise HTTPException(status_code=404, detail="Subtopic not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value:
            subtopic.slug = _unique_slug(db, Subtopic, value, exclude_id=subtopic.id, scope_filter=Subtopic.topic_id == subtopic.topic_id)
        setattr(subtopic, field, value)
    db.flush()
    log_action(db, admin.id, "update", "subtopic", subtopic.id)
    return subtopic


@router.delete("/subtopics/{subtopic_id}", response_model=Message)
def delete_subtopic(subtopic_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    subtopic = db.get(Subtopic, subtopic_id)
    if subtopic is None:
        raise HTTPException(status_code=404, detail="Subtopic not found")
    db.delete(subtopic)
    db.flush()
    log_action(db, admin.id, "delete", "subtopic", subtopic_id)
    return Message(detail="Subtopic deleted")
