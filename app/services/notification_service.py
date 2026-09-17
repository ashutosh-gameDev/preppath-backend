"""
Student notification feed = persisted `notifications` rows (achievements,
system messages). Exam/ExamEvent-based reminders (application window, admit
card, exam date, result) were removed along with the whole Exam concept -
see models/exam.py's git history if that ever needs reviving. Job vacancy
alerts live separately, in models/job_posting.py + the student /jobs feed.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


def get_feed(db: Session, user_id: uuid.UUID, limit: int = 30) -> list[dict]:
    persisted = db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "ref_type": n.ref_type,
            "ref_id": n.ref_id,
            "is_read": n.is_read,
            "created_at": n.created_at,
            "event_date": None,
            "external_link": None,
        }
        for n in persisted
    ]


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    type_: str,
    title: str,
    message: str,
    ref_type: str | None = None,
    ref_id: uuid.UUID | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id, type=type_, title=title, message=message, ref_type=ref_type, ref_id=ref_id
    )
    db.add(n)
    db.flush()
    return n
