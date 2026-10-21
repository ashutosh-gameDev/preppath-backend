"""
Admin CRUD for CourseNotePage - official, admin-authored notes shown to
every student enrolled in a course. Gated on require_content_access (like
questions/tests/PYQ papers), not require_admin - content_editor accounts can
author notes as part of everyday content work. Not ownership-scoped (unlike
PYQ papers): notes aren't tied to intern payments, so any content team
member can see/edit any course's notes, same as Courses/Subjects/Topics.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.db.session import get_db
from app.models.course import Subject
from app.models.course_notes import CourseNotePage
from app.models.user import User
from app.schemas.common import Message
from app.schemas.course_notes import CourseNotePageAdminOut, CourseNotePageIn, CourseNotePageUpdate

router = APIRouter(prefix="/admin/course-notes", tags=["admin:course-notes"])


@router.get("", response_model=list[CourseNotePageAdminOut])
def list_course_notes(
    course_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    return db.execute(
        select(CourseNotePage).where(CourseNotePage.course_id == course_id).order_by(CourseNotePage.order_index)
    ).scalars().all()


@router.post("", response_model=CourseNotePageAdminOut)
def create_course_note(
    course_id: uuid.UUID,
    payload: CourseNotePageIn,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    subject = db.get(Subject, payload.subject_id)
    if subject is None or subject.course_id != course_id:
        raise HTTPException(status_code=400, detail="Subject does not belong to this course")
    page = CourseNotePage(course_id=course_id, created_by=admin.id, **payload.model_dump())
    db.add(page)
    db.flush()
    return page


@router.patch("/{page_id}", response_model=CourseNotePageAdminOut)
def update_course_note(
    page_id: uuid.UUID,
    payload: CourseNotePageUpdate,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    page = db.get(CourseNotePage, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Note page not found")
    data = payload.model_dump(exclude_unset=True)
    if "subject_id" in data:
        subject = db.get(Subject, data["subject_id"])
        if subject is None or subject.course_id != page.course_id:
            raise HTTPException(status_code=400, detail="Subject does not belong to this course")
    for field, value in data.items():
        setattr(page, field, value)
    db.flush()
    return page


@router.delete("/{page_id}", response_model=Message)
def delete_course_note(page_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    page = db.get(CourseNotePage, page_id)
    if page is not None:
        db.delete(page)
        db.flush()
    return Message(detail="Deleted")
