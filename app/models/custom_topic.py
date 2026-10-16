import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class CustomTopic(Base, UUIDPKMixin, TimestampMixin):
    """
    A student's own personal checklist item added under one subject in
    their Syllabus view - distinct from admin-authored `Topic` rows (shared
    CRM content every student sees). Lets a student track something the
    official syllabus doesn't cover, without needing a CRM content change.
    Deliberately NOT folded into Topic/TopicProgress - it's private to the
    student who created it, and doesn't affect /practice/continue's
    syllabus-progress metric (that stays about official content only).
    """
    __tablename__ = "custom_topics"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
