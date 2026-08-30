import uuid
from datetime import date

from app.schemas.common import ORMModel


class MetricWithTrend(ORMModel):
    value: float
    previous_value: float
    change_pct: float | None  # None when previous_value == 0 (no basis for comparison)
    direction: str  # "up" | "down" | "flat"


class PerformanceOverview(ORMModel):
    questions_attempted: MetricWithTrend
    accuracy: MetricWithTrend
    tests_completed: MetricWithTrend
    average_score_pct: MetricWithTrend
    avg_time_per_question_seconds: MetricWithTrend
    xp_earned: MetricWithTrend
    current_rank: int | None
    period_days: int


class ProgressPoint(ORMModel):
    date: date
    accuracy: float | None
    questions_solved: int
    avg_test_score: float | None
    xp: int
    study_time_minutes: float


class TopicPerformance(ORMModel):
    topic_id: uuid.UUID
    topic_name: str
    attempts: int
    accuracy: float
    is_strong: bool
    is_weak: bool
    last_attempted: str | None


class SubjectPerformance(ORMModel):
    subject_id: uuid.UUID
    subject_name: str
    attempts: int
    accuracy: float
    topics: list[TopicPerformance] = []


class StrengthWeaknessItem(ORMModel):
    subject_id: uuid.UUID | None
    topic_id: uuid.UUID | None
    name: str
    scope: str  # "subject" | "topic"
    accuracy: float
    attempts: int


class ImprovementItem(ORMModel):
    subject_id: uuid.UUID
    subject_name: str
    previous_accuracy: float
    current_accuracy: float
    change_pct: float
    previous_attempts: int
    current_attempts: int


class RecommendationOut(ORMModel):
    id: str
    title: str
    reason: str
    action: str  # "practice_weak" | "practice_stale" | "challenge_hard"
    course_id: uuid.UUID | None
    subject_id: uuid.UUID | None
    topic_id: uuid.UUID | None
    difficulty: str | None
    question_count: int
    estimated_minutes: int


class LeaderboardEntry(ORMModel):
    rank: int
    user_id: uuid.UUID
    full_name: str | None
    avatar_url: str | None
    score: float
    accuracy: float
    questions_attempted: int
    is_current_user: bool = False


class LeaderboardOut(ORMModel):
    scope: str
    scope_label: str
    entries: list[LeaderboardEntry]
    current_user_rank: int | None
    current_user_entry: LeaderboardEntry | None = None
