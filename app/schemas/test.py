import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class TestSectionIn(ORMModel):
    name: str
    order_index: int = 0
    num_questions: int = 0


class TestQuestionIn(ORMModel):
    question_id: uuid.UUID
    section_name: str | None = None
    order_index: int = 0
    marks: float = 1
    negative_marks: float = 0


class AutoSelectRule(ORMModel):
    """One row of an automatic test-builder rule, e.g. '25 questions from Quant, medium difficulty'."""
    section_name: str
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None = None
    difficulty: str | None = None
    count: int
    marks: float = 1
    negative_marks: float = 0


class TestCreate(ORMModel):
    title: str
    test_type: str = "mock"
    course_id: uuid.UUID | None = None
    exam_id: uuid.UUID | None = None
    pyq_year: int | None = None
    pyq_paper_label: str | None = None
    duration_minutes: int = 60
    negative_marking: float = 0
    difficulty: str | None = None
    instructions: str | None = None
    status: str = "draft"
    # Manual selection:
    questions: list[TestQuestionIn] = []
    sections: list[TestSectionIn] = []
    # OR automatic selection:
    auto_rules: list[AutoSelectRule] = []


class TestUpdate(ORMModel):
    title: str | None = None
    duration_minutes: int | None = None
    negative_marking: float | None = None
    difficulty: str | None = None
    instructions: str | None = None
    status: str | None = None


class TestSectionOut(ORMModel):
    id: uuid.UUID
    name: str
    order_index: int
    num_questions: int


class TestListItemOut(ORMModel):
    id: uuid.UUID
    title: str
    test_type: str
    course_id: uuid.UUID | None
    exam_id: uuid.UUID | None
    pyq_year: int | None
    pyq_paper_label: str | None
    duration_minutes: int
    total_questions: int
    total_marks: float
    negative_marking: float
    difficulty: str | None
    status: str
    attempted: bool = False
    best_score: float | None = None


class TestDetailOut(TestListItemOut):
    instructions: str | None
    sections: list[TestSectionOut] = []


class TestQuestionForAttemptOut(ORMModel):
    """Question shown while the test is in progress - no answer key."""
    order_index: int
    section_name: str | None
    marks: float
    negative_marks: float
    question: dict  # QuestionAttemptOut serialized (avoids circular import)


class TestAttemptStartOut(ORMModel):
    test_attempt_id: uuid.UUID
    test: TestDetailOut
    started_at: datetime
    questions: list[TestQuestionForAttemptOut]


class SubmittedAnswer(ORMModel):
    question_id: uuid.UUID
    selected_option: str | None = None
    time_taken_seconds: int = 0


class TestSubmitRequest(ORMModel):
    answers: list[SubmittedAnswer]


class SectionResult(ORMModel):
    name: str
    correct: int
    incorrect: int
    skipped: int
    score: float
    accuracy: float


class TestResultOut(ORMModel):
    test_attempt_id: uuid.UUID
    test_id: uuid.UUID
    test_title: str
    score: float
    total_marks: float
    percentage: float
    correct_count: int
    incorrect_count: int
    skipped_count: int
    accuracy: float
    time_taken_seconds: int
    rank: int | None
    total_participants: int
    section_results: list[SectionResult]


class TestAttemptHistoryItem(ORMModel):
    test_attempt_id: uuid.UUID
    test_id: uuid.UUID
    test_title: str
    test_type: str
    status: str
    score: float
    total_marks: float
    accuracy: float
    submitted_at: datetime | None
