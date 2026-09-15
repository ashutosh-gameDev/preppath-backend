import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class PaperCreate(ORMModel):
    exam_name: str
    year: int | None = None
    label: str | None = None
    language: str | None = None
    course_id: uuid.UUID | None = None


class PaperUpdate(ORMModel):
    exam_name: str | None = None
    year: int | None = None
    label: str | None = None
    language: str | None = None
    course_id: uuid.UUID | None = None


class PaperOut(ORMModel):
    id: uuid.UUID
    exam_name: str
    year: int | None
    label: str | None
    language: str | None
    course_id: uuid.UUID | None
    created_at: datetime
    # How many questions currently carry this paper_id - lets the admin form/
    # bulk-edit picker and the test builder's "load from paper" list show
    # which papers actually have content without a second request.
    question_count: int = 0
