import uuid
from datetime import date, datetime

from app.schemas.common import ORMModel


class JobPostingCreate(ORMModel):
    title: str
    organization: str | None = None
    description: str | None = None
    job_type: str = "government"
    stream: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    qualification: str | None = None
    category: str | None = None
    gender: str = "all"
    apply_link: str | None = None
    salary: str | None = None
    application_fee: str | None = None
    age_relaxation: str | None = None
    course_id: uuid.UUID | None = None
    posted_date: date
    application_deadline: date | None = None
    is_published: bool = False


class JobPostingUpdate(ORMModel):
    title: str | None = None
    organization: str | None = None
    description: str | None = None
    job_type: str | None = None
    stream: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    qualification: str | None = None
    category: str | None = None
    gender: str | None = None
    apply_link: str | None = None
    salary: str | None = None
    application_fee: str | None = None
    age_relaxation: str | None = None
    course_id: uuid.UUID | None = None
    posted_date: date | None = None
    application_deadline: date | None = None
    is_published: bool | None = None


class JobPostingOut(ORMModel):
    id: uuid.UUID
    title: str
    organization: str | None
    description: str | None
    job_type: str
    stream: str | None
    min_age: int | None
    max_age: int | None
    qualification: str | None
    category: str | None
    gender: str
    apply_link: str | None
    salary: str | None
    application_fee: str | None
    age_relaxation: str | None
    course_id: uuid.UUID | None
    posted_date: date
    application_deadline: date | None
    is_published: bool
    created_at: datetime


class JobPostingBulkImportRequest(ORMModel):
    postings: list[JobPostingCreate]


class JobPostingBulkImportResult(ORMModel):
    imported: int
    postings: list[JobPostingOut]
