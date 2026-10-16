import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPKMixin


class StudySession(Base, UUIDPKMixin):
    """
    One completed Study Timer session - logged when the student hits Reset
    (or navigates away) after the timer accumulated time. Append-only, same
    convention as Attempt/XPTransaction - the monthly leaderboard is a sum
    of this table, never a separately-maintained counter.
    """
    __tablename__ = "study_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class LeaderboardReward(Base, UUIDPKMixin):
    """
    Records that a given (period, rank) has already been paid out, so the
    lazy monthly distribution (study_leaderboard_service.maybe_distribute_rewards,
    run whenever anyone loads the leaderboard after month-end) never grants
    the same month's rewards twice. Also doubles as the CRM's "past
    winners" history.
    """
    __tablename__ = "leaderboard_rewards"
    __table_args__ = (UniqueConstraint("period", "rank_position", name="uq_leaderboard_reward_period_rank"),)

    # "YYYY-MM" - the calendar month this ranking was computed over.
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    total_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
