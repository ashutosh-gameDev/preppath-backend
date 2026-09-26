import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, Sequence, String, Table, Text, text
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

    # RESTRICT, not CASCADE: deleting a course/subject must never silently
    # destroy the questions inside it (that is exactly how content was lost
    # before). The admin delete endpoints turn this into a clear 409.
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    # Finer than topic_id (Topic = "chapter", Subtopic = "topic" in the
    # product's own vocabulary) - optional, independent of topic_id being
    # set, so existing rows and imports that only know the chapter keep
    # working. SET NULL on delete, same as topic_id, so removing a subtopic
    # from the syllabus never cascades into deleting questions.
    subtopic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subtopics.id", ondelete="SET NULL"), nullable=True
    )
    # Which PYQ paper this question is from (see models/pyq_paper.py).
    # Nullable at the DB level so existing untagged rows aren't
    # forced through a backfill, but required by QuestionCreate going
    # forward - see that schema's docstring.
    pyq_paper_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pyq_papers.id", ondelete="SET NULL"), nullable=True
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
    # Free text rather than an enum so a new language never needs a
    # migration, matching the extensibility approach used for question_type.
    # Independent of `pyq_paper_id` - a question's own language, not the paper's.
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ContentStatus.DRAFT, nullable=False, index=True)

    # Set when a bulk import (or an admin by hand) noticed the source
    # material references a picture that isn't attached yet - e.g. "refer to
    # the diagram below" with no diagram. `image_note` is a short reminder of
    # what's missing. Lets the CRM filter straight to these instead of an
    # admin re-reading every question to find the ones missing a picture.
    # Cleared automatically the moment an image is actually added - see
    # admin/questions.py.
    needs_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    image_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    tags: Mapped[list["Tag"]] = relationship(secondary=question_tags)

    course = relationship("Course")
    subject = relationship("Subject")
    topic = relationship("Topic")
    subtopic = relationship("Subtopic")
    pyq_paper = relationship("PYQPaper")
    created_by_user = relationship("User")

    # Read-only pass-throughs to the linked PYQPaper, kept under their old
    # names (`year`/`source`/`exam_name` were plain columns/a property
    # reading straight off Exam before this split) so
    # QuestionAttemptOut/QuestionReviewOut and every consumer of them
    # (student flashcards/PYQ review) keep working unchanged -
    # Pydantic's from_attributes reads a property exactly like a column.
    # Storage/tagging happens through `pyq_paper_id`/`pyq_paper` only; these
    # are display convenience, not settable.
    @property
    def year(self) -> int | None:
        return self.pyq_paper.year if self.pyq_paper else None

    @property
    def source(self) -> str | None:
        return self.pyq_paper.label if self.pyq_paper else None

    @property
    def exam_name(self) -> str | None:
        return self.pyq_paper.exam_name if self.pyq_paper else None

    @property
    def uploader_label(self) -> str | None:
        """Who added this question, for the admin list - a content_editor
        (intern) account's human-facing username if it has one (see
        User.username), else the account's real name, else its email. None
        if created_by is unset (a pre-existing row from before this was
        tracked) or the user account was since deleted (ON DELETE SET NULL)."""
        u = self.created_by_user
        if not u:
            return None
        return u.username or u.full_name or u.email
