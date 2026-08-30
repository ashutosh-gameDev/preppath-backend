import uuid
from datetime import date, datetime, timezone

from pydantic import EmailStr, computed_field

from app.schemas.common import ORMModel


class ProfileOut(ORMModel):
    xp_total: int
    level: int
    current_streak: int
    longest_streak: int
    last_activity_date: date | None
    daily_goal_questions: int
    questions_attempted: int
    questions_correct: int
    tests_completed: int
    pyqs_completed: int
    premium_until: datetime | None = None

    # @computed_field (not a bare @property) so these actually appear in the
    # serialized JSON - a plain property is invisible to Pydantic v2's
    # serializer.
    @computed_field
    @property
    def accuracy(self) -> float:
        if self.questions_attempted == 0:
            return 0.0
        return round(100 * self.questions_correct / self.questions_attempted, 1)

    @computed_field
    @property
    def is_premium(self) -> bool:
        return self.premium_until is not None and self.premium_until > datetime.now(timezone.utc)


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    username: str | None = None
    full_name: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    created_at: datetime
    profile: ProfileOut | None = None


class UserUpdateMe(ORMModel):
    full_name: str | None = None
    avatar_url: str | None = None
    daily_goal_questions: int | None = None


class AdminUserListItem(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    last_active_at: datetime | None
    xp_total: int = 0
    questions_attempted: int = 0
    accuracy: float = 0.0
    tests_completed: int = 0


class AdminUserStatusUpdate(ORMModel):
    is_active: bool
