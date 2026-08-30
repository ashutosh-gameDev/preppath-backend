import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import UserRole


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
    # Premium (ad-free) access expiry - null/past = free tier. Extended by
    # services/premium_service.py whenever a Payment is confirmed paid;
    # stacks on top of any remaining time rather than overwriting it.
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")
