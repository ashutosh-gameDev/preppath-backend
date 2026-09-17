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
    tier: str = "normal"
    tier_expires_at: datetime | None = None
    date_of_birth: date | None = None
    qualification: str | None = None

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
    def effective_tier(self) -> str:
        """`tier` once it lapses back to "normal" - mirrors
        premium_service.effective_tier so the frontend never has to
        replicate the expiry check itself."""
        if self.tier == "normal":
            return "normal"
        if self.tier_expires_at is None or self.tier_expires_at <= datetime.now(timezone.utc):
            return "normal"
        return self.tier

    @computed_field
    @property
    def is_premium(self) -> bool:
        """True for either paid tier (Pro or Premium) - kept named
        `is_premium` since that's the flag both frontends already gate
        ads/course-limit on."""
        return self.effective_tier != "normal"


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
    date_of_birth: date | None = None
    qualification: str | None = None


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
    tier: str = "normal"
    tier_expires_at: datetime | None = None


class AdminUserStatusUpdate(ORMModel):
    is_active: bool


class AdminUserTierUpdate(ORMModel):
    """Manual override from the Users admin page - lets a super admin
    comp/adjust a student's tier directly, independent of the Razorpay
    purchase flow (services/premium_service.grant_premium)."""
    tier: str
    tier_expires_at: datetime | None = None
