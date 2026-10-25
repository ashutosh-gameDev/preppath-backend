import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPKMixin


class DeviceToken(Base, UUIDPKMixin):
    """
    A Firebase Cloud Messaging registration token for one installed app on
    one device, for one user - a user can have several (phone + tablet, or
    a reinstall leaving behind a stale one Firebase will just reject
    silently on send). `token` itself is the unique identity; re-registering
    the same token (e.g. the app re-registers on every launch) just updates
    `user_id`/`updated_at` on the existing row via an upsert, covering both
    "a new device" and "this token now belongs to a different logged-in
    user" (shared/reused device) in one write - see register_device_token.
    """
    __tablename__ = "device_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(20), default="android", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
