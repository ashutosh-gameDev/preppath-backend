import uuid
from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Reminder(Base, UUIDPKMixin, TimestampMixin):
    """
    A student's own "remind me to study/sleep/whatever" entry - "daily"
    (fires every day at `time_of_day`) or "once" (fires only on `on_date`,
    at `time_of_day`). Purely a schedule: delivery is entirely client-side
    (the student's own browser polls the clock and shows a Notification
    while the app is open - see student-web's use-reminder-checker.ts),
    there is no server-side push/cron behind this.
    """
    __tablename__ = "reminders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    # "daily" | "once"
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="daily")
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    # Only set (and only meaningful) for kind="once" - null for "daily".
    on_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
