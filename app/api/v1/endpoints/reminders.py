"""
A student's own reminders ("remind me to study/sleep at X") - plain CRUD,
scoped to the caller. See models/reminder.py for why there's no delivery
logic at all here: the student's own browser checks these against the
clock and shows a Notification while the app is open.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.reminder import Reminder
from app.models.user import User
from app.schemas.common import Message
from app.schemas.reminder import ReminderCreate, ReminderOut, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.execute(
        select(Reminder).where(Reminder.user_id == user.id).order_by(Reminder.time_of_day)
    ).scalars().all()


@router.post("", response_model=ReminderOut)
def create_reminder(payload: ReminderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = Reminder(**payload.model_dump(), user_id=user.id)
    db.add(reminder)
    db.flush()
    return reminder


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: uuid.UUID,
    payload: ReminderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = db.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Reminder not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(reminder, field, value)
    # A switch back to "daily" always drops any one-time date it had as a
    # "once" reminder - never leave a stale on_date sitting on a daily one.
    if reminder.kind == "daily":
        reminder.on_date = None
    db.flush()
    return reminder


@router.delete("/{reminder_id}", response_model=Message)
def delete_reminder(reminder_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminder = db.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(reminder)
    db.flush()
    return Message(detail="Reminder deleted")
