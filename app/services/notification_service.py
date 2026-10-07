"""
Student notification feed = persisted `notifications` rows (achievements,
system messages, job alerts). Exam/ExamEvent-based reminders (application
window, admit card, exam date, result) were removed along with the whole
Exam concept - see models/exam.py's git history if that ever needs
reviving. Job postings themselves still live in models/job_posting.py and
the student /jobs feed reads them directly - a Notification row here is
just the "you're eligible for a new one" alert, created once per student
per posting (see notify_eligible_students_for_job).
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import NotificationType
from app.models.job_posting import JobPosting
from app.models.notification import Notification
from app.models.user import Profile


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


def notify_eligible_students_for_job(db: Session, job: JobPosting) -> int:
    """Called once, exactly when a job posting goes from draft to published
    (see admin/job_postings.py) - never on a later edit of an already-
    published posting, or every student would get re-notified on every
    typo fix. A student is eligible the same way GET /jobs already filters
    them: null min/max age or qualification means "no restriction"; age is
    computed from their own `Profile.date_of_birth`, which they set once
    from the Jobs tab - a student who never set it is simply not matched,
    same as they'd see nothing in /jobs without it either."""
    age = func.extract("year", func.age(func.current_date(), Profile.date_of_birth))
    conditions = [Profile.date_of_birth.is_not(None)]
    if job.min_age is not None:
        conditions.append(age >= job.min_age)
    if job.max_age is not None:
        conditions.append(age <= job.max_age)
    if job.qualification:
        conditions.append(Profile.qualification.ilike(job.qualification))
    user_ids = db.execute(select(Profile.user_id).where(*conditions)).scalars().all()
    for user_id in user_ids:
        create_notification(
            db, user_id, NotificationType.JOB_POSTING, job.title,
            f"You're eligible for this job posting{f' at {job.organization}' if job.organization else ''}.",
            ref_type="job_posting", ref_id=job.id,
        )
    return len(user_ids)
