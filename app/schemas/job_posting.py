import uuid
from datetime import date, datetime

from app.schemas.common import ORMModel


class JobPostingCreate(ORMModel):
    title: str
    organization: str | None = None
    description: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    qualification: str | None = None
    apply_link: str | None = None
    course_id: uuid.UUID | None = None
    posted_date: date
    application_deadline: date | None = None
    is_published: bool = False


class JobPostingUpdate(ORMModel):
    title: str | None = None
    organization: str | None = None
    description: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    qualification: str | None = None
    apply_link: str | None = None
    course_id: uuid.UUID | None = None
    posted_date: date | None = None
    application_deadline: date | None = None
    is_published: bool | None = None


class JobPostingOut(ORMModel):
    id: uuid.UUID
    title: str
    organization: str | None
    description: str | None
    min_age: int | None
    max_age: int | None
    qualification: str | None
    apply_link: str | None
    course_id: uuid.UUID | None
    posted_date: date
    application_deadline: date | None
    is_published: bool
    created_at: datetime
