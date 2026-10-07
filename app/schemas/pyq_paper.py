import uuid
from datetime import datetime

from app.schemas.common import ORMModel
from app.schemas.question import QuestionReviewOut


class PYQPaperCreate(ORMModel):
    exam_name: str
    year: int | None = None
    label: str | None = None
    language: str | None = None
    course_id: uuid.UUID | None = None


class PYQPaperUpdate(ORMModel):
    # Publishing/unpublishing is super-admin only (checked in the endpoint).
    is_published: bool | None = None
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
    is_published: bool = False
    created_at: datetime
    # How many questions currently carry this pyq_paper_id - lets the admin
    # form/bulk-edit picker and the test builder's "load from paper" list
    # show which papers actually have content without a second request.
    question_count: int = 0
    # Who created this paper tag - None for legacy rows with no known
    # uploader, or if the uploader account was since deleted.
    uploaded_by: str | None = None


class PYQPaperStudentOut(ORMModel):
    """A published paper as a student sees it in the PYQ browser."""
    id: uuid.UUID
    name: str
    exam_name: str
    year: int | None
    label: str | None
    language: str | None
    course_id: uuid.UUID
    question_count: int
    # Distinct questions of this paper the student has already answered.
    attempted_count: int = 0


class PYQPaperProgressOut(ORMModel):
    attempted_ids: list[uuid.UUID]


class PyqAnswerIn(ORMModel):
    question_id: uuid.UUID
    selected_option: str | None = None  # null = skipped
    time_taken_seconds: int = 0


class PyqSubmitRequest(ORMModel):
    """One shot for the whole paper - the attempt page holds every answer in
    local state (no per-question network call) and only talks to the
    server here. Unlike a Test, there's no persisted "attempt" row to start
    first - a PYQ paper's questions are already fetched, answer-free, from
    GET /pyq/papers/{id}/questions."""
    answers: list[PyqAnswerIn]


class PyqSubmitResult(ORMModel):
    correct_count: int
    incorrect_count: int
    skipped_count: int
    accuracy: float
    review: list[QuestionReviewOut]
