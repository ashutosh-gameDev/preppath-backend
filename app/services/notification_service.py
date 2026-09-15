"""
Student notification feed = live-computed upcoming exam-event reminders
merged with persisted `notifications` rows (achievements, system messages).
See `models/notification.py` for why exam events aren't fanned out into rows.

Exam-event delivery is course-based, not follow-based: a student sees an
event if it targets no specific courses (global) or targets a course
they're enrolled in (`CourseEnrollment`) - no "follow this exam" step
required. See ExamEvent's docstring in models/exam.py.
"""
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enrollment import CourseEnrollment
from app.models.exam import Exam, ExamEvent
from app.models.notification import Notification

UPCOMING_WINDOW_DAYS = 45


def get_feed(db: Session, user_id: uuid.UUID, limit: int = 30) -> list[dict]:
    today = date.today()
    horizon = today + timedelta(days=UPCOMING_WINDOW_DAYS)

    enrolled_course_ids = set(
        db.execute(select(CourseEnrollment.course_id).where(CourseEnrollment.user_id == user_id)).scalars().all()
    )

    candidates = db.execute(
        select(ExamEvent, Exam.name)
        .join(Exam, Exam.id == ExamEvent.exam_id)
        .options(selectinload(ExamEvent.courses))
        .where(
            ExamEvent.is_published.is_(True),
            ExamEvent.event_date >= today,
            ExamEvent.event_date <= horizon,
        )
        .order_by(ExamEvent.event_date.asc())
    ).all()
    # Course-scope filter done in Python (not SQL) - an event's course list
    # is small and this window is already a small candidate set, and it
    # avoids an outer-join/distinct dance for "no course rows = global".
    event_rows = [
        (ev, exam_name)
        for ev, exam_name in candidates
        if not ev.courses or {c.id for c in ev.courses} & enrolled_course_ids
    ]

    feed = []
    for ev, exam_name in event_rows:
        days_left = (ev.event_date - today).days
        feed.append(
            {
                "id": f"event-{ev.id}",
                "type": "exam_event",
                "title": f"{exam_name}: {ev.title}",
                "message": ev.description or f"{ev.title} in {days_left} day(s).",
                "ref_type": "exam_event",
                "ref_id": ev.id,
                "is_read": False,
                "created_at": ev.created_at if hasattr(ev, "created_at") else None,
                "event_date": ev.event_date,
                "external_link": ev.external_link,
            }
        )

    persisted = db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    ).scalars().all()
    for n in persisted:
        feed.append(
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
        )

    feed.sort(key=lambda f: f["event_date"] or f["created_at"].date() if f["created_at"] else today)
    return feed[:limit]


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
