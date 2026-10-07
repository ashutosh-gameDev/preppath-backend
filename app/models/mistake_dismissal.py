import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPKMixin


class MistakeDismissal(Base, UUIDPKMixin):
    """
    A student manually clearing a question off their Mistake Book
    (`analytics.latest_wrong_attempts`) without having to answer it
    correctly again. The Mistake Book is otherwise fully derived from
    `Attempt` with no flag of its own (see that function's docstring) - this
    is the one piece of state layered on top: a question stays hidden only
    until the NEXT wrong attempt on it (`dismissed_at` compared against that
    question's latest wrong-attempt time), so dismissing isn't a permanent
    "never show me this again".
    """
    __tablename__ = "mistake_dismissals"
    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_mistake_dismissal"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dismissed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
