import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPKMixin


class VideoWatch(Base, UUIDPKMixin):
    """One student having watched one video. Videos aren't their own content
    rows - they're plain URLs on Topic.video_url / Subtopic.youtube_videos -
    so this ledger keys on (user_id, video_url) directly rather than an FK to
    a Video table that doesn't exist. Same per-user-completion shape as
    TopicProgress, just keyed by URL instead of topic_id."""
    __tablename__ = "video_watches"
    __table_args__ = (UniqueConstraint("user_id", "video_url", name="uq_video_watches_user_url"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")
