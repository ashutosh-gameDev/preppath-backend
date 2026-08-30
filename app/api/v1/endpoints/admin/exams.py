import uuid

from fastapi import APIRouter, Depends, HTTPException
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_content_access
from app.db.session import get_db
from app.models.exam import Exam
from app.models.user import User
from app.schemas.common import Message
from app.schemas.exam import ExamCreate, ExamOut, ExamUpdate
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/exams", tags=["admin:exams"])


def _unique_slug(db: Session, name: str, exclude_id: uuid.UUID | None = None) -> str:
    base = slugify(name)
    slug = base
    i = 1
    while True:
        q = select(Exam).where(Exam.slug == slug)
        if exclude_id:
            q = q.where(Exam.id != exclude_id)
        if db.execute(q).scalar_one_or_none() is None:
            return slug
        i += 1
        slug = f"{base}-{i}"


@router.get("", response_model=list[ExamOut])
def list_exams(admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    # GET on require_content_access (like admin/courses) - content_editor
    # accounts need to read exams to tag a question/paper to one.
    return db.execute(select(Exam).order_by(Exam.name)).scalars().all()


@router.post("", response_model=ExamOut)
def create_exam(payload: ExamCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    slug = _unique_slug(db, payload.name)
    exam = Exam(**payload.model_dump(), slug=slug)
    db.add(exam)
    db.flush()
    log_action(db, admin.id, "create", "exam", exam.id)
    return exam


@router.patch("/{exam_id}", response_model=ExamOut)
def update_exam(exam_id: uuid.UUID, payload: ExamUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "name" and value:
            exam.slug = _unique_slug(db, value, exclude_id=exam.id)
        setattr(exam, field, value)
    db.flush()
    log_action(db, admin.id, "update", "exam", exam.id)
    return exam


@router.delete("/{exam_id}", response_model=Message)
def delete_exam(exam_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    db.delete(exam)
    db.flush()
    log_action(db, admin.id, "delete", "exam", exam_id)
    return Message(detail="Exam deleted")
