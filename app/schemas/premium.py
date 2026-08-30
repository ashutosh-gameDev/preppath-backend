import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class PlanOut(ORMModel):
    key: str
    label: str
    amount_paise: int
    amount_rupees: float
    duration_days: int


class CheckoutRequest(ORMModel):
    plan: str


class CheckoutResponse(ORMModel):
    payment_id: uuid.UUID
    dev_mode: bool
    # Real Razorpay checkout fields (empty in dev_mode):
    razorpay_order_id: str | None = None
    razorpay_key_id: str | None = None
    amount_paise: int
    currency: str = "INR"
    plan: str


class VerifyRequest(ORMModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class DevCompleteRequest(ORMModel):
    payment_id: uuid.UUID


class PremiumStatusOut(ORMModel):
    is_premium: bool
    premium_until: datetime | None
    plans: list[PlanOut]
