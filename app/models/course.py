import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Course(Base, UUIDPKMixin, TimestampMixin):
    """A course/exam family, e.g. 'SSC CGL', 'UPSC CSE'. Fully admin-defined."""
    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Bumped by admins in the CRM whenever a course's questions/papers get a
    # meaningful update - lets students who've downloaded a paper for
    # offline attempts (see student-web lib/paper-cache.ts) know their local
    # copy may be stale, without any automatic re-sync magic.
    content_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    subjects: Mapped[list["Subject"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Subject.order_index"
    )


class Subject(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("course_id", "slug", name="uq_subject_course_slug"),)

    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="subjects")
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan", order_by="Topic.order_index"
    )


class Topic(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("subject_id", "slug", name="uq_topic_subject_slug"),)

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Optional syllabus video lecture (YouTube link) - shown alongside the
    # topic in the student "Syllabus" tab, separate from practice questions.
    # Kept even though a topic can now also have subtopics with their own
    # video lists - this is the "whole chapter overview" video, if any.
    video_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="topics")
    subtopics: Mapped[list["Subtopic"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", order_by="Subtopic.order_index"
    )


class Subtopic(Base, UUIDPKMixin, TimestampMixin):
    """A finer breakdown within a topic (e.g. Topic 'Kinematics' ->
    Subtopic 'Projectile Motion') - each can carry its own list of video
    lessons, unlike a Topic which has at most one overview video_url."""
    __tablename__ = "subtopics"
    __table_args__ = (UniqueConstraint("topic_id", "slug", name="uq_subtopic_topic_slug"),)

    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    youtube_videos: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    topic: Mapped["Topic"] = relationship(back_populates="subtopics")


class TopicProgress(Base, UUIDPKMixin):
    """A student's mark-complete/incomplete state on a syllabus topic (the
    video lecture, not question practice - that progress is already derived
    from `attempts`). One row per (user, topic); upserted from a single
    'mark complete' toggle in the UI. `needs_revision` is independent of
    `is_completed` - a topic can be finished AND flagged to revisit before
    the exam, so the two aren't mutually exclusive states."""
    __tablename__ = "topic_progress"
    __table_args__ = (UniqueConstraint("user_id", "topic_id", name="uq_topic_progress_user_topic"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    needs_revision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
