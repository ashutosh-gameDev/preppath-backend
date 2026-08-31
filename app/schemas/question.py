import uuid
from datetime import datetime

from pydantic import field_validator

from app.schemas.common import ORMModel

VALID_OPTIONS = {"A", "B", "C", "D"}
VALID_DIFFICULTY = {"easy", "medium", "hard"}
VALID_STATUS = {"draft", "published", "archived"}


class QuestionBase(ORMModel):
    question_text: str
    image_url: str | None = None
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    # Optional per-option images (e.g. one choice is a diagram) - independent
    # of image_url (the question-stem image); most questions leave these null.
    option_a_image: str | None = None
    option_b_image: str | None = None
    option_c_image: str | None = None
    option_d_image: str | None = None
    correct_option: str
    explanation: str | None = None
    difficulty: str = "medium"
    question_type: str = "practice"
    year: int | None = None
    source: str | None = None
    # Free text, not an enum, so a new language never needs a migration -
    # same reasoning as question_type. e.g. "English", "Hindi".
    language: str | None = None
    tags: list[str] = []

    @field_validator("tags", mode="before")
    @classmethod
    def _tags_as_strings(cls, v: list) -> list[str]:
        # Inbound (create/update request bodies) this is already a list of
        # plain strings. Outbound (QuestionAdminOut built straight from the
        # Question ORM object) `tags` is the `Tag` relationship - a list of
        # Tag objects, not strings - so it needs unwrapping to `.name` here
        # or every response with a non-empty tag list 500s on serialization
        # (only ever went unnoticed because every prior test used tags=[]).
        if v is None:
            return []
        return [item.name if hasattr(item, "name") and not isinstance(item, str) else item for item in v]

    @field_validator("correct_option")
    @classmethod
    def validate_correct_option(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in VALID_OPTIONS:
            raise ValueError("correct_option must be one of A, B, C, D")
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_DIFFICULTY:
            raise ValueError("difficulty must be one of easy, medium, hard")
        return v

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, v: str | None) -> str | None:
        v = (v or "").strip()
        return v or None


class QuestionCreate(QuestionBase):
    course_id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None = None
    exam_id: uuid.UUID | None = None
    status: str = "draft"


class QuestionUpdate(ORMModel):
    question_text: str | None = None
    image_url: str | None = None
    option_a: str | None = None
    option_b: str | None = None
    option_c: str | None = None
    option_d: str | None = None
    option_a_image: str | None = None
    option_b_image: str | None = None
    option_c_image: str | None = None
    option_d_image: str | None = None
    correct_option: str | None = None
    explanation: str | None = None
    difficulty: str | None = None
    question_type: str | None = None
    year: int | None = None
    source: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    course_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    exam_id: uuid.UUID | None = None
    status: str | None = None


class QuestionAdminOut(QuestionBase):
    """Full question payload including the answer - admin / review use only."""
    id: uuid.UUID
    # Short sequential number ("Q1042") assigned once at creation, for
    # referencing/searching a question without pasting its UUID - see
    # migration 0005. Never set by the client, always DB-assigned.
    display_number: int
    course_id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None
    exam_id: uuid.UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class QuestionAttemptOut(ORMModel):
    """
    What the student receives WHILE answering - correct_option and
    explanation are deliberately omitted so they can't be read from the
    network response before submitting. See QuestionReviewOut for the
    post-submit shape.
    """
    id: uuid.UUID
    question_text: str
    image_url: str | None
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    option_a_image: str | None = None
    option_b_image: str | None = None
    option_c_image: str | None = None
    option_d_image: str | None = None
    difficulty: str
    question_type: str
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None
    # Paper tag (exam + year + source + language), shown as a badge in
    # flashcards/PYQ browsing when the question was tagged to a specific
    # paper - all null for ordinary practice questions.
    year: int | None = None
    source: str | None = None
    language: str | None = None
    exam_name: str | None = None


class QuestionReviewOut(QuestionAttemptOut):
    correct_option: str
    explanation: str | None


class ReportQuestionRequest(ORMModel):
    question_id: uuid.UUID
    reason: str
    description: str | None = None


class BulkImportRowError(ORMModel):
    row_number: int
    errors: list[str]
    raw: dict


class BulkImportPreview(ORMModel):
    """
    Stateless preview: the backend parses + validates the uploaded file and
    hands back every valid row plus a per-row error report. No server-side
    cache/token is needed - the admin frontend either (a) lets the admin
    review and POSTs `valid_rows` straight to the commit endpoint, or (b) the
    admin fixes the source file and re-uploads for a fresh preview.
    """
    total_rows: int
    valid_count: int
    invalid_count: int
    errors: list[BulkImportRowError]
    valid_rows: list[QuestionCreate]


class BulkImportDefaults(ORMModel):
    """Paper-level fields filled in once on the 'Upload Paper' screen and
    applied to every row that doesn't specify its own value - lets a bulk
    file skip course/subject/exam/year/source columns entirely when they're
    the same for the whole paper (the normal case)."""
    course_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    exam_id: uuid.UUID | None = None
    year: int | None = None
    source: str | None = None
    language: str | None = None
    difficulty: str | None = None
    question_type: str | None = None
    # Bulk-imported rows always land as drafts regardless (see
    # bulk_import_commit) - review before publishing, same as before.


class BulkImportCommitRequest(ORMModel):
    rows: list[QuestionCreate]


class BulkImportCommitResult(ORMModel):
    imported: int
    skipped: int
