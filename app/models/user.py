import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import UserRole, UserTier


class User(Base, TimestampMixin):
    """
    Mirrors a row in Supabase `auth.users`. `id` MUST equal the Supabase auth
    user id (the backend never creates auth users itself - it only creates a
    matching row here the first time an authenticated request from a new
    user is seen, via `get_or_create_user`).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # Set only for content_editor (intern) accounts created via /admin/team -
    # their real "email" is a synthetic address (see admin/team.py) they never
    # see; this is the human-facing username they actually log in with.
    username: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.STUDENT, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Unique per user, generated once at account creation (see
    # api/deps.get_current_user) - shared via a WhatsApp link so a friend's
    # signup can be attributed back to this account (see referral_service.py).
    referral_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    # Set at most once, by POST /referrals/claim, shortly after THIS user's
    # own account was created - who referred them in, if anyone. Null for
    # everyone who signed up organically.
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Same claim (POST /referrals/claim), but for a super-admin-created
    # marketing code (see models/referral_campaign.py) instead of another
    # student's personal code - mutually exclusive with `referred_by` (one
    # claim per account, whichever kind of code it was).
    signup_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("referral_campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )

    profile: Mapped["Profile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Profile(Base, TimestampMixin):
    """
    Cached/derived student statistics. Source of truth for these numbers is
    always the ledger tables (`attempts`, `xp_transactions`, `test_attempts`);
    this table exists purely so the homepage/profile can render in a single
    cheap lookup instead of aggregating the full attempt history on every
    request. Updated transactionally by the services that write attempts/XP.
    """
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    xp_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_goal_questions: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tests_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pyqs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Subscription tier - NORMAL (free), PRO, or PREMIUM (see enums.UserTier).
    # `tier_expires_at` is when the CURRENT paid tier lapses back to NORMAL;
    # irrelevant while tier is NORMAL. Settable two ways: automatically by
    # services/premium_service.py when a Payment is confirmed paid (stacks
    # on top of any remaining time rather than overwriting it), or manually
    # by a super admin from the Users admin page (comps, support overrides).
    tier: Mapped[str] = mapped_column(String(20), default=UserTier.NORMAL, nullable=False)
    tier_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Optional, set once from the Jobs notification tab (or the profile) and
    # remembered - used to filter job postings to ones the student is
    # actually eligible for. Free text for qualification (e.g. "Graduate"),
    # same reasoning as other free-text taxonomy fields in this codebase.
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Self-reported - used both for Jobs eligibility filtering and (city/
    # state only) CRM ad targeting, see Ad.states/Ad.cities in models/ad.py.
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "male" | "female" | "other"
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "General" | "OBC" | "SC" | "ST" | "EWS" | "PWD"

    user: Mapped["User"] = relationship(back_populates="profile")
