import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class QuestionBookmark(Base, UUIDPKMixin, TimestampMixin):
    """
    A question the student saved for later - shown in the "Bookmarks" tool.
    Deliberately separate from `Attempt` (a question can be bookmarked
    without ever having been answered, e.g. spotted while browsing a PYQ
    paper) and from the Mistake Book (a bookmark is a deliberate save, not a
    wrong answer).
    """
    __tablename__ = "question_bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_question_bookmark"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
