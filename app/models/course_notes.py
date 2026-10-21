import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class CourseNotePage(Base, UUIDPKMixin, TimestampMixin):
    """An admin-authored note page shown to every student enrolled in its
    course - official content, not a student's own personal Notes Board
    (see models/notes.py for that, a fully separate, per-user table).
    `canvas_json` is the same serialized Konva-stage shape the personal
    Notes editor produces (opaque to the backend) - the CRM editor is a
    ported copy of that same canvas component."""
    __tablename__ = "course_note_pages"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled")
    # "grid-dark" | "grid-gray" - which graph-paper background style.
    background: Mapped[str] = mapped_column(String(20), nullable=False, default="grid-dark")
    canvas_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Draft until an admin publishes it - students only ever see published
    # pages, same convention as Course/Topic/Subtopic/PYQPaper.is_published.
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
