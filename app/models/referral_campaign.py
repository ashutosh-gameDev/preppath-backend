import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class ReferralCampaign(Base, UUIDPKMixin, TimestampMixin):
    """
    A super-admin-chosen custom code for offline/local marketing (a college
    poster, a local shop tie-up, a WhatsApp group in one city) - distinct
    from a student's own auto-generated `User.referral_code` (see
    referral_service.py). Shares the same claim endpoint (POST
    /referrals/claim) and the same 1-hour post-signup claim window, but the
    reward (if any) goes to the NEW student who typed the code, not to a
    referrer - there's no referring student to reward for a marketing code.
    """
    __tablename__ = "referral_campaigns"

    # Admin-chosen, not random - e.g. "JAIPUR10". Longer than User.referral_code
    # (String(12)) since a memorable marketing code is often a whole word/phrase.
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # Internal-only description of the campaign (e.g. "Jaipur college poster,
    # Jan 2026") - never shown to students.
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    # Days of Pro granted to the new student who signs up with this code - 0
    # means a pure tracking code with no signup incentive.
    reward_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Lets an admin stop a code from being claimed (e.g. a campaign ended)
    # without losing its signup history - deliberately no delete endpoint.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by_user = relationship("User", foreign_keys=[created_by])
