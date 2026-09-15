"""
Import every model module so `Base.metadata` is fully populated for Alembic
autogenerate and `create_all` (used only in tests). Keep this list in sync
whenever a new model module is added.
"""
from app.models.base import Base  # noqa: F401
from app.models.user import User, Profile  # noqa: F401
from app.models.course import Course, Subject, Topic, TopicProgress  # noqa: F401
from app.models.question import Question, Tag, question_tags  # noqa: F401
from app.models.exam import Exam, ExamEvent, UserExamFollow  # noqa: F401
from app.models.enrollment import CourseEnrollment  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.test import Test, TestSection, TestQuestion, TestAttempt  # noqa: F401
from app.models.attempt import Attempt  # noqa: F401
from app.models.gamification import XPTransaction, Achievement, UserAchievement  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.admin import Report, AdminActivityLog, PlatformSetting  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Profile",
    "Course",
    "Subject",
    "Topic",
    "TopicProgress",
    "Question",
    "Tag",
    "question_tags",
    "Exam",
    "ExamEvent",
    "UserExamFollow",
    "CourseEnrollment",
    "Payment",
    "Test",
    "TestSection",
    "TestQuestion",
    "TestAttempt",
    "Attempt",
    "XPTransaction",
    "Achievement",
    "UserAchievement",
    "Notification",
    "Report",
    "AdminActivityLog",
    "PlatformSetting",
]
