"""Admin management of exam notifications (`ExamEvent` rows) - application
windows, admit card, exam date, result, etc. See models/exam.py."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.exam import Exam, ExamEvent
from app.models.user import User
from app.schemas.common import Message
from app.schemas.exam import ExamEventCreate, ExamEventOut, ExamEventUpdate
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/notifications", tags=["admin:notifications"])


@router.get("", response_model=list[ExamEventOut])
def list_notifications(exam_id: uuid.UUID | None = None, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = select(ExamEvent)
    if exam_id:
        q = q.where(ExamEvent.exam_id == exam_id)
    return db.execute(q.order_by(ExamEvent.event_date.desc())).scalars().all()


@router.post("/exam/{exam_id}", response_model=ExamEventOut)
def create_notification(exam_id: uuid.UUID, payload: ExamEventCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    event = ExamEvent(**payload.model_dump(), exam_id=exam_id)
    db.add(event)
    db.flush()
    log_action(db, admin.id, "create", "exam_event", event.id)
    return event


@router.patch("/{event_id}", response_model=ExamEventOut)
def update_notification(event_id: uuid.UUID, payload: ExamEventUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    event = db.get(ExamEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.flush()
    log_action(db, admin.id, "update", "exam_event", event.id)
    return event


@router.delete("/{event_id}", response_model=Message)
def delete_notification(event_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    event = db.get(ExamEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(event)
    db.flush()
    log_action(db, admin.id, "delete", "exam_event", event_id)
    return Message(detail="Notification deleted")
