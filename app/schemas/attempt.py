import uuid
from datetime import datetime

from app.schemas.common import ORMModel
from app.schemas.question import QuestionReviewOut


class PracticeSessionRequest(ORMModel):
    """Request a batch of practice questions."""
    course_id: uuid.UUID
    subject_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = None
    difficulty: str | None = None
    question_type: str = "practice"
    count: int = 20
    exclude_attempted: bool = True


class PracticeAnswerRequest(ORMModel):
    question_id: uuid.UUID
    selected_option: str | None = None  # null = skipped
    time_taken_seconds: int = 0
    # Used only when practicing from within a "continue practice" session so
    # progress can be tracked per course/subject/topic without a test wrapper.
    course_id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None = None


class PracticeAnswerResult(ORMModel):
    is_correct: bool | None
    correct_option: str
    explanation: str | None
    xp_earned: int
    question: QuestionReviewOut
    streak_current: int
    xp_total: int


class AttemptOut(ORMModel):
    id: uuid.UUID
    question_id: uuid.UUID
    course_id: uuid.UUID
    subject_id: uuid.UUID
    topic_id: uuid.UUID | None
    selected_option: str | None
    is_correct: bool | None
    time_taken_seconds: int
    difficulty: str
    question_type: str
    attempted_at: datetime
