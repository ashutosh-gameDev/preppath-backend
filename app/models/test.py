import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ContentStatus, Difficulty, TestAttemptStatus, TestType


class Test(Base, UUIDPKMixin, TimestampMixin):
    """
    A fixed, timed set of questions. Powers BOTH mock tests and PYQ papers
    (`test_type` distinguishes them) rather than duplicating sections/
    questions/attempts machinery across two parallel schemas - a PYQ paper is
    structurally a test (duration, marks, negative marking, question list)
    that happens to be tagged with the exam/year/shift it came from.
    """
    __tablename__ = "tests"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    test_type: Mapped[str] = mapped_column(String(10), default=TestType.MOCK, nullable=False, index=True)

    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # PYQ-specific grouping: Exam -> year -> paper label (e.g. "Tier 1 Shift 1")
    pyq_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    pyq_paper_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    marks_per_question: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    negative_marking: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=ContentStatus.DRAFT, nullable=False, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    sections: Mapped[list["TestSection"]] = relationship(
        back_populates="test", cascade="all, delete-orphan", order_by="TestSection.order_index"
    )
    test_questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="test", cascade="all, delete-orphan", order_by="TestQuestion.order_index"
    )
    exam = relationship("Exam")
    course = relationship("Course")


class TestSection(Base, UUIDPKMixin):
    """e.g. '25 Quant / 25 Reasoning / 25 English / 25 GA' sections of a test."""
    __tablename__ = "test_sections"

    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    test: Mapped["Test"] = relationship(back_populates="sections")


class TestQuestion(Base, UUIDPKMixin):
    """Join table: which questions belong to a test, in what order/section, at what marks."""
    __tablename__ = "test_questions"

    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_sections.id", ondelete="SET NULL"), nullable=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    marks: Mapped[float] = mapped_column(Float, default=1, nullable=False)
    negative_marks: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    test: Mapped["Test"] = relationship(back_populates="test_questions")
    question = relationship("Question")


class TestAttempt(Base, UUIDPKMixin):
    """One student's attempt at a Test (mock or PYQ). Individual question
    responses are stored in `attempts` (Attempt.test_attempt_id links back
    here) so all analytics read from a single attempts table regardless of
    whether the question was solved standalone or inside a test."""
    __tablename__ = "test_attempts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default=TestAttemptStatus.IN_PROGRESS, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    test: Mapped["Test"] = relationship()
    user = relationship("User")
