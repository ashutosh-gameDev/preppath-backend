import uuid
from datetime import datetime

from app.schemas.common import ORMModel
from app.schemas.question import QuestionAdminOut, QuestionReviewOut


class PYQPaperCreate(ORMModel):
    exam_name: str
    year: int | None = None
    label: str | None = None
    language: str | None = None
    course_id: uuid.UUID | None = None
    max_marks: float | None = None
    time_limit_minutes: int | None = None


class PYQPaperUpdate(ORMModel):
    # Publishing/unpublishing is super-admin only (checked in the endpoint).
    is_published: bool | None = None
    exam_name: str | None = None
    year: int | None = None
    label: str | None = None
    language: str | None = None
    course_id: uuid.UUID | None = None
    max_marks: float | None = None
    time_limit_minutes: int | None = None
    # Super-admin only (checked in the endpoint) - what this paper pays its
    # uploader. Null clears the override back to the platform default rate.
    payment_amount_paise: int | None = None


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
    # Of those, how many still have needs_image=True - lets the papers list
    # show upload/crop progress ("12 of 40 need images") without a separate
    # Fill Images round-trip just to find out.
    needs_image_count: int = 0
    # Who created this paper tag - None for legacy rows with no known
    # uploader, or if the uploader account was since deleted.
    uploaded_by: str | None = None
    # The raw id behind uploaded_by - lets the super-admin papers list filter
    # by uploader without a second lookup (two uploaders could share a
    # display name; the id can't collide).
    created_by: uuid.UUID | None = None
    # How many of this paper's questions have at least one image filled in
    # (image_url or any of the 4 option images) - a super-admin-only metric
    # for spotting which papers are still mostly text.
    image_count: int = 0
    # Optional, admin-set per paper - null hides the stat on the student
    # landing page; a null time_limit_minutes means no countdown/auto-submit.
    max_marks: float | None = None
    time_limit_minutes: int | None = None
    # This paper's own payout override (paise) - null means "use the
    # platform default rate" (see intern_payment_service.resolve_rate).
    # Resolved to an actual number for display alongside this field by the
    # caller when needed (e.g. the intern payments summary).
    payment_amount_paise: int | None = None


class PYQPaperPreviewOut(ORMModel):
    """The whole paper as rendered for the cross-team Preview page - any
    team member can open any paper here regardless of who created it, since
    reviewing finished content (unlike in-progress uploading) is meant to be
    everyone's job, not just the uploader's."""
    paper: PYQPaperOut
    questions: list[QuestionAdminOut]


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
    # Admin-set per paper, both optional - null hides the stat on the
    # landing page; a null time_limit_minutes means no countdown/auto-submit
    # on the attempt page.
    max_marks: float | None = None
    time_limit_minutes: int | None = None


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


class PyqTopicAnalytics(ORMModel):
    topic_id: uuid.UUID
    topic_name: str
    correct: int
    incorrect: int
    skipped: int
    total: int
    accuracy: float


class PyqSubjectAnalytics(ORMModel):
    subject_id: uuid.UUID
    subject_name: str
    correct: int
    incorrect: int
    skipped: int
    total: int
    accuracy: float
    topics: list[PyqTopicAnalytics]


class PyqPaperAnalyticsOut(ORMModel):
    """Subject/topic breakdown of this student's latest attempt on each of
    this paper's questions - "how did I do, broken down by subject/topic",
    not a per-session snapshot (PYQ papers have no persisted attempt/session
    row, unlike Tests - re-attempting a question just moves which attempt
    counts as "latest")."""
    subjects: list[PyqSubjectAnalytics]
