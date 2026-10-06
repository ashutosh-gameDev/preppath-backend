import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin

ad_courses = Table(
    "ad_courses",
    Base.metadata,
    Column("ad_id", UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
)


class Ad(Base, UUIDPKMixin, TimestampMixin):
    """
    A CRM-managed ad card shown in a named placement in student-web (e.g.
    `dashboard-mid`, the dashboard's AdSlot; `results-bottom`, the test
    results page's AdSlot) - see components/shared/ad-slot.tsx on that side.
    `placement` is free text, not an enum, matching the extensibility
    reasoning used for Question.language/question_type: a new slot never
    needs a migration, just a new `slot="..."` call site.

    `courses` targets the ad to one or more specific courses (e.g. an SSC
    CGL coaching ad shown only to SSC CGL students) - an empty list means
    untargeted, shown regardless of course, same "empty/null = no
    restriction" convention as JobPosting.course_id.
    """
    __tablename__ = "ads"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    placement: Mapped[str] = mapped_column(String(50), nullable=False, default="dashboard-mid", index=True)
    # Higher wins when several active ads share a placement/window.
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by_user = relationship("User")
    courses = relationship("Course", secondary=ad_courses)


class AdEvent(Base, UUIDPKMixin):
    """One impression or click on an Ad - a plain event log (not a counter)
    so CTR can be recomputed exactly and a future per-day breakdown needs no
    schema change. See admin/ads.py for the impressions/clicks/ctr rollup."""
    __tablename__ = "ad_events"

    ad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "impression" | "click"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ad = relationship("Ad")
