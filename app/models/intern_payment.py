import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPKMixin


class InternPayment(Base, UUIDPKMixin):
    """One payout recorded against an intern (content_editor) account - a
    plain append-only ledger (like AdEvent), not a mutable running balance:
    'amount paid' is always SUM(amount_paise) for that user, recomputed, so
    there's never a stored total to drift out of sync. See
    intern_payment_service.compute_summary for how this combines with
    PYQPaper.payment_amount_paise to produce earned/paid/remaining."""
    __tablename__ = "intern_payments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # Who recorded this payment - SET NULL (not a reason to ever hide a real
    # payout) if that admin account is later deleted.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", foreign_keys=[user_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
