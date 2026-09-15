import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class PYQPaperCreate(ORMModel):
    exam_name: str
    year: int | None = None
    label: str | None = None
    language: str | None = None
    course_id: uuid.UUID | None = None


class PYQPaperUpdate(ORMModel):
    exam_name: str | None = None
    year: int | None = None
    label: str | None = None
    language: str | None = None
    course_id: uuid.UUID | None = None


class PYQPaperOut(ORMModel):
    id: uuid.UUID
    exam_name: str
    year: int | None
    label: str | None
    language: str | None
    course_id: uuid.UUID | None
    created_at: datetime
    # How many questions currently carry this pyq_paper_id - lets the admin
    # form/bulk-edit picker and the test builder's "load from paper" list
    # show which papers actually have content without a second request.
    question_count: int = 0
