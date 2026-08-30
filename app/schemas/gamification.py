import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class AchievementOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str
    icon: str | None
    xp_reward: int
    earned: bool = False
    earned_at: datetime | None = None
    progress_current: int = 0
    progress_target: int = 0


class XPTransactionOut(ORMModel):
    id: uuid.UUID
    amount: int
    reason: str
    created_at: datetime


class DailyChallengeOut(ORMModel):
    date: str
    course_id: uuid.UUID | None
    question_count: int
    estimated_minutes: int
    xp_available: int
    completed: bool
    questions_done: int
