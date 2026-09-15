import uuid
from datetime import date

from app.schemas.common import ORMModel


class ExamEventBase(ORMModel):
    event_type: str = "other"
    title: str
    description: str | None = None
    event_date: date
    external_link: str | None = None
    is_published: bool = True


class ExamEventCreate(ExamEventBase):
    # Which course(s) see this as a notification - empty means everyone
    # (global), matching Exam.course_id's own "unset = for everyone"
    # convention. See ExamEvent's docstring for the delivery rule.
    course_ids: list[uuid.UUID] = []


class ExamEventUpdate(ORMModel):
    event_type: str | None = None
    title: str | None = None
    description: str | None = None
    event_date: date | None = None
    external_link: str | None = None
    is_published: bool | None = None
    course_ids: list[uuid.UUID] | None = None


class ExamEventOut(ExamEventBase):
    id: uuid.UUID
    exam_id: uuid.UUID
    # Read off ExamEvent.course_ids, a plain property over the `courses`
    # relationship (see models/exam.py) - from_attributes reads a property
    # exactly like a column, so no separate unwrapping is needed here.
    course_ids: list[uuid.UUID] = []


class ExamBase(ORMModel):
    name: str
    description: str | None = None
    conducting_body: str | None = None
    is_published: bool = False


class ExamCreate(ExamBase):
    course_id: uuid.UUID | None = None


class ExamUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    conducting_body: str | None = None
    is_published: bool | None = None
    course_id: uuid.UUID | None = None


class ExamOut(ExamBase):
    id: uuid.UUID
    slug: str
    course_id: uuid.UUID | None


class ExamDetailOut(ExamOut):
    events: list[ExamEventOut] = []
    is_followed: bool = False
    follower_count: int = 0


class ExamWithCountdown(ExamOut):
    next_event: ExamEventOut | None = None
    days_remaining: int | None = None
    notifications_enabled: bool = True
