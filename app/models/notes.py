import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class NoteCategory(Base, UUIDPKMixin, TimestampMixin):
    """A student's own folder for grouping Notes Board pages, e.g. "Physics"
    or "Revision". Purely a Premium-tier server mirror - Normal/Pro users
    have categories too, but theirs never leave IndexedDB (see student-web
    lib/notes-db.ts); this table only exists to sync a Premium student's
    pages across devices."""
    __tablename__ = "note_categories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Swatch color for the category tab/badge, e.g. "#f97316".
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#6366f1")


class NotePage(Base, UUIDPKMixin, TimestampMixin):
    """One Notes Board canvas. `id` is CLIENT-generated (a student can create
    pages entirely offline before ever syncing) - the sync endpoint is an
    upsert keyed on that id, last-write-wins by `updated_at`, not a
    server-assigned-id create flow. `canvas_json` is the serialized Konva
    stage (shapes/lines/text/images) exactly as the editor produced it -
    opaque to the backend, which never needs to understand its contents."""
    __tablename__ = "note_pages"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("note_categories.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled")
    # "grid-dark" | "grid-gray" - which graph-paper background style.
    background: Mapped[str] = mapped_column(String(20), nullable=False, default="grid-dark")
    canvas_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    category = relationship("NoteCategory")
