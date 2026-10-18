import uuid
from datetime import datetime
from typing import Literal

from app.schemas.common import ORMModel

AdFormat = Literal["banner", "fullscreen"]


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
    # Empty = untargeted, shown regardless of course/state/city.
    course_ids: list[uuid.UUID] = []
    states: list[str] = []
    cities: list[str] = []
    format: AdFormat = "banner"
    max_impressions: int | None = None
    max_clicks: int | None = None
    interstitial_every_n: int | None = None


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
    states: list[str] | None = None
    cities: list[str] | None = None
    format: AdFormat | None = None
    max_impressions: int | None = None
    max_clicks: int | None = None
    interstitial_every_n: int | None = None


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
    states: list[str] = []
    cities: list[str] = []
    format: AdFormat = "banner"
    max_impressions: int | None = None
    max_clicks: int | None = None
    interstitial_every_n: int | None = None
    # Computed from ad_events - see admin/ads.py.
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    # Computed, not stored - why this ad has effectively stopped serving
    # even though `is_active` (the admin's own toggle) still reads true.
    # See admin/ads.py's _auto_paused_reason.
    auto_paused_reason: str | None = None


class AdPublicOut(ORMModel):
    """What the student app needs to render and splice in one ad - nothing
    about targeting or performance."""
    id: uuid.UUID
    title: str
    image_url: str | None
    link_url: str | None
    body_text: str | None
    format: AdFormat = "banner"
    interstitial_every_n: int | None = None


class AdEventIn(ORMModel):
    event_type: Literal["impression", "click"]
