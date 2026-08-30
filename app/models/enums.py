"""
Python-level enums shared by models, schemas and services.

These are stored as plain `String` columns (validated by Pydantic/Python at
the application layer) rather than native Postgres ENUM types. That keeps the
set of allowed values extensible (e.g. adding a new QuestionType or
ExamEventType later) with an application deploy instead of an
`ALTER TYPE ... ADD VALUE` migration.
"""
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return str(self.value)


class UserRole(StrEnum):
    STUDENT = "student"
    # Restricted admin-panel account for interns/content team: can manage
    # questions and tests/PYQ papers only (see api/deps.require_content_access)
    # - never courses, users, settings, or exam notifications. Created only by
    # a super admin via /admin/team, never via self-signup.
    CONTENT_EDITOR = "content_editor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CorrectOption(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class QuestionType(StrEnum):
    """Extensible: new values can be added without a schema migration."""
    PRACTICE = "practice"
    PYQ = "pyq"
    MOCK = "mock"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TestType(StrEnum):
    MOCK = "mock"
    PYQ = "pyq"


class TestAttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    ABANDONED = "abandoned"


class ExamEventType(StrEnum):
    APPLICATION_START = "application_start"
    APPLICATION_END = "application_end"
    ADMIT_CARD = "admit_card"
    EXAM_DATE = "exam_date"
    RESULT = "result"
    OTHER = "other"


class XPReason(StrEnum):
    QUESTION_CORRECT = "question_correct"
    QUESTION_ATTEMPT = "question_attempt"
    TEST_COMPLETED = "test_completed"
    DAILY_CHALLENGE = "daily_challenge"
    STREAK_BONUS = "streak_bonus"
    ACHIEVEMENT = "achievement"


class ReportStatus(StrEnum):
    OPEN = "open"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"


class NotificationType(StrEnum):
    EXAM_EVENT = "exam_event"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"
    LEADERBOARD = "leaderboard"


class LeaderboardScope(StrEnum):
    GLOBAL = "global"
    EXAM = "exam"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SUBJECT = "subject"


class AchievementCriteria(StrEnum):
    """What an achievement's `criteria_value` is measured against."""
    QUESTIONS_ATTEMPTED = "questions_attempted"
    TESTS_COMPLETED = "tests_completed"
    ACCURACY_PCT = "accuracy_pct"
    STREAK_DAYS = "streak_days"
    GLOBAL_RANK_TOP_N = "global_rank_top_n"
    PYQ_COMPLETED = "pyq_completed"
    FIRST_TEST = "first_test"
