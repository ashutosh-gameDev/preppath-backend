import uuid
from datetime import datetime
from typing import Literal

from app.schemas.common import ORMModel


class AdCreate(ORMModel):
    title: str
    image_url: str | None = None
    link_url: str | None = None
    body_text: str | None = None
    placement: str = "dashboard-mid"
    priority: int = 0
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    # Empty = untargeted, shown regardless of course.
    course_ids: list[uuid.UUID] = []


class AdUpdate(ORMModel):
    title: str | None = None
    image_url: str | None = None
    link_url: str | None = None
    body_text: str | None = None
    placement: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    course_ids: list[uuid.UUID] | None = None


class AdOut(ORMModel):
    id: uuid.UUID
    title: str
    image_url: str | None
    link_url: str | None
    body_text: str | None
    placement: str
    priority: int
    is_active: bool
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    course_ids: list[uuid.UUID] = []
    # Computed from ad_events - see admin/ads.py.
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0


class AdPublicOut(ORMModel):
    """What the student app needs to render one ad - nothing about targeting
    or performance."""
    id: uuid.UUID
    title: str
    image_url: str | None
    link_url: str | None
    body_text: str | None


class AdEventIn(ORMModel):
    event_type: Literal["impression", "click"]
