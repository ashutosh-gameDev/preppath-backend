import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ContentStatus, Difficulty


class Deck(Base, UUIDPKMixin, TimestampMixin):
    """
    An AI-generated 'Study Bite' interactive flashcard deck - a title/
    taxonomy shell around one JSON blob (`cards`) holding the deck's full
    card/block content exactly as validated by
    app.schemas.deck.DeckPayload/deck_import_service. Not normalized into
    per-card/per-block tables: the content is a single AI-authored unit that
    is always read/written whole (like AdminActivityLog.extra /
    PlatformSetting.value), never queried block-by-block.
    """
    __tablename__ = "decks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # RESTRICT, matching Question: deleting a course/subject must never
    # silently destroy decks inside it.
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    subtopic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subtopics.id", ondelete="SET NULL"), nullable=True
    )

    difficulty: Mapped[str] = mapped_column(String(10), default=Difficulty.MEDIUM, nullable=False)
    # Free text (matches Course.icon/Subtopic background-style fields) - one
    # of the prompt's allowed background theme names, cosmetic only.
    theme: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # The full validated `deck.cards` array (each card's type, background and
    # blocks) - see app/schemas/deck.py for the shape enforced before this is
    # ever written.
    cards: Mapped[list[dict]] = mapped_column(JSON, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=ContentStatus.DRAFT, nullable=False, index=True)

    # SET NULL, not RESTRICT: unlike course/subject (never silently destroy
    # content), losing track of *who* created a deck if their account is
    # later deleted is an acceptable, non-destructive loss - matches
    # Question.created_by.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    course = relationship("Course")
    subject = relationship("Subject")
    topic = relationship("Topic")
    subtopic = relationship("Subtopic")
    created_by_user = relationship("User")

    @property
    def card_count(self) -> int:
        return len(self.cards or [])
