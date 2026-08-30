import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ContentStatus, CorrectOption, Difficulty, QuestionType

question_tags = Table(
    "question_tags",
    Base.metadata,
    Column("question_id", UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base, UUIDPKMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Question(Base, UUIDPKMixin, TimestampMixin):
    """
    Single-correct-answer MCQ with exactly four inline options. A separate
    `question_options` table was considered (per the brief) but rejected for
    v1: every question type in scope (practice/PYQ/mock) uses the same fixed
    A/B/C/D shape, so inline columns avoid an extra join on the hottest read
    path (practice/test fetching) without losing anything. Revisit if a
    variable-option-count question type (e.g. multi-select) is added later.
    """
    __tablename__ = "questions"

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL"), nullable=True
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional per-option images (e.g. a diagram as one of the choices) -
    # independent of `image_url` (the question-stem image) and of each other;
    # most questions leave all four null.
    option_a_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    option_b_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    option_c_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    option_d_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)  # CorrectOption
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    difficulty: Mapped[str] = mapped_column(String(10), default=Difficulty.MEDIUM, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), default=QuestionType.PRACTICE, nullable=False, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ContentStatus.DRAFT, nullable=False, index=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    tags: Mapped[list["Tag"]] = relationship(secondary=question_tags)

    course = relationship("Course")
    subject = relationship("Subject")
    topic = relationship("Topic")
    exam = relationship("Exam")

    @property
    def exam_name(self) -> str | None:
        """Convenience for schemas (e.g. QuestionAttemptOut) that want to show
        the paper tag (exam + year + source) without the caller needing its
        own exam lookup - Pydantic's from_attributes picks up plain properties
        the same way it picks up columns."""
        return self.exam.name if self.exam else None
