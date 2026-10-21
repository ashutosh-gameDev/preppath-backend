"""
Student read access to CourseNotePage - official, admin-authored notes for
a course (distinct from the personal Notes Board, see endpoints/notes.py).
Only published pages, and only for courses the student is enrolled in.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.course_notes import CourseNotePage
from app.models.enrollment import CourseEnrollment
from app.models.user import User
from app.schemas.course_notes import CourseNotePageMetaOut, CourseNotePageStudentOut

router = APIRouter(prefix="/course-notes", tags=["course-notes"])


def _require_enrolled(db: Session, user: User, course_id: uuid.UUID) -> None:
    enrolled = db.execute(
        select(CourseEnrollment.id).where(CourseEnrollment.user_id == user.id, CourseEnrollment.course_id == course_id)
    ).first()
    if enrolled is None:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")


@router.get("", response_model=list[CourseNotePageMetaOut])
def list_course_notes(course_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_enrolled(db, user, course_id)
    return db.execute(
        select(CourseNotePage)
        .where(CourseNotePage.course_id == course_id, CourseNotePage.is_published.is_(True))
        .order_by(CourseNotePage.order_index)
    ).scalars().all()


@router.get("/{page_id}", response_model=CourseNotePageStudentOut)
def get_course_note(page_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    page = db.get(CourseNotePage, page_id)
    if page is None or not page.is_published:
        raise HTTPException(status_code=404, detail="Note page not found")
    _require_enrolled(db, user, page.course_id)
    return page
