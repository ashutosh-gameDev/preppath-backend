import uuid

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Sequence, String, Table, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ContentStatus, CorrectOption, Difficulty, QuestionFormat, QuestionType

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
    __table_args__ = (
        # Mirrors the conditional requirement Pydantic already enforces
        # (QuestionBase._validate_format) at the DB layer too, so a bad
        # INSERT/UPDATE that bypasses the API can't leave a half-formed row:
        # an MCQ needs all 4 options + a correct_option; a fill-in-the-blank
        # needs correct_answer_text and nothing else.
        CheckConstraint(
            "(question_format = 'mcq' AND option_a IS NOT NULL AND option_b IS NOT NULL "
            "AND option_c IS NOT NULL AND option_d IS NOT NULL AND correct_option IS NOT NULL) "
            "OR "
            "(question_format = 'fill_blank' AND correct_answer_text IS NOT NULL)",
            name="ck_questions_format_fields",
        ),
    )

    # Short, stable, human-friendly number ("Q1042") so a question can be
    # referenced/searched by admins/interns without pasting a UUID - never
    # reused, assigned once at insert via a dedicated DB sequence (see
    # migration 0005) rather than derived from row count so it survives
    # deletes without shifting.
    display_number: Mapped[int] = mapped_column(
        Integer,
        Sequence("questions_display_number_seq"),
        server_default=text("nextval('questions_display_number_seq')"),
        unique=True,
        nullable=False,
        index=True,
    )

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

    # "mcq" (default, original shape - 4 inline options) or "fill_blank" (a
    # single free-text correct answer, no options at all). See
    # ck_questions_format_fields above for which fields each format requires.
    question_format: Mapped[str] = mapped_column(String(20), default=QuestionFormat.MCQ, nullable=False, index=True)

    # NULL for a fill_blank question - required for mcq (enforced by
    # ck_questions_format_fields, not by the column itself, since which
    # fields are required depends on question_format).
    option_a: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_b: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_c: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_d: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional per-option images (e.g. a diagram as one of the choices) -
    # independent of `image_url` (the question-stem image) and of each other;
    # most questions leave all four null.
    option_a_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    option_b_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    option_c_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    option_d_image: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    correct_option: Mapped[str | None] = mapped_column(String(1), nullable=True)  # CorrectOption, mcq only
    # The accepted answer for a fill_blank question - NULL for mcq.
    correct_answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    difficulty: Mapped[str] = mapped_column(String(10), default=Difficulty.MEDIUM, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), default=QuestionType.PRACTICE, nullable=False, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Paper-level tag, same family as year/source (e.g. "English", "Hindi") -
    # free text rather than an enum so a new language never needs a
    # migration, matching the extensibility approach used for question_type.
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
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
