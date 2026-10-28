import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class ReferralCampaignCreate(ORMModel):
    code: str
    label: str
    reward_days: int = 0


class ReferralCampaignUpdate(ORMModel):
    label: str | None = None
    reward_days: int | None = None
    is_active: bool | None = None


class ReferralCampaignOut(ORMModel):
    id: uuid.UUID
    code: str
    label: str
    reward_days: int
    is_active: bool
    created_at: datetime
    signup_count: int
