"""Shared course/subject/topic helpers - slug generation used by both the
one-at-a-time admin endpoints (admin/courses.py) and the bulk course
importer (course_import_service.py)."""
import uuid

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session


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
