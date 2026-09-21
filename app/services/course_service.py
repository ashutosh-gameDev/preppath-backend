"""Shared course/subject/topic helpers - slug generation used by both the
one-at-a-time admin endpoints (admin/courses.py) and the bulk course
importer (course_import_service.py)."""
import uuid

from slugify import slugify
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.course import Subject, Subtopic, Topic


def unique_slug(db: Session, model, name: str, exclude_id: uuid.UUID | None = None, scope_filter=None) -> str:
    # slugify() can come back empty for a name with no Latin-transliterable
    # characters at all (rare, but possible for e.g. an all-symbol name) -
    # fall back to a generic base rather than looping forever appending "-N"
    # to an empty string.
    base = slugify(name) or "item"
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


def publish_course_tree(db: Session, course_id: uuid.UUID) -> dict[str, int]:
    """Publishes every subject, chapter (topic) and subtopic under a course.
    Students only ever see published syllabus items, so publishing just the
    course row would show them an empty course. Returns how many of each were
    switched on (already-published ones are left alone and not counted)."""
    subject_ids = select(Subject.id).where(Subject.course_id == course_id)
    topic_ids = select(Topic.id).where(Topic.subject_id.in_(subject_ids))
    subjects = db.execute(
        update(Subject).where(Subject.course_id == course_id, Subject.is_published.is_(False)).values(is_published=True)
    ).rowcount
    topics = db.execute(
        update(Topic).where(Topic.subject_id.in_(subject_ids), Topic.is_published.is_(False)).values(is_published=True)
    ).rowcount
    subtopics = db.execute(
        update(Subtopic).where(Subtopic.topic_id.in_(topic_ids), Subtopic.is_published.is_(False)).values(is_published=True)
    ).rowcount
    return {"subjects": subjects, "topics": topics, "subtopics": subtopics}
