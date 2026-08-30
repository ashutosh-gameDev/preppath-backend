import uuid
from datetime import date, datetime

from app.schemas.common import ORMModel


class NotificationOut(ORMModel):
    id: uuid.UUID | str
    type: str
    title: str
    message: str
    ref_type: str | None
    ref_id: uuid.UUID | None
    is_read: bool
    created_at: datetime
    event_date: date | None = None
    external_link: str | None = None


class UserExamFollowOut(ORMModel):
    exam_id: uuid.UUID
    notifications_enabled: bool
