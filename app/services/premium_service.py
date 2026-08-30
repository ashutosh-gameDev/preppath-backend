"""
Premium (ad-free) plans and the logic to grant/extend access after a payment
is confirmed. Amounts are in paise (Razorpay's smallest INR unit, like cents)
- 1 rupee = 100 paise.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.user import Profile


@dataclass(frozen=True)
class Plan:
    key: str
    label: str
    amount_paise: int
    duration_days: int


PLANS: dict[str, Plan] = {
    "monthly": Plan(key="monthly", label="Monthly", amount_paise=5000, duration_days=30),
    "half_yearly": Plan(key="half_yearly", label="6 Months", amount_paise=25000, duration_days=180),
    "yearly": Plan(key="yearly", label="Yearly", amount_paise=50000, duration_days=365),
}


def get_plan(key: str) -> Plan | None:
    return PLANS.get(key)


def is_premium(profile: Profile) -> bool:
    return profile.premium_until is not None and profile.premium_until > datetime.now(timezone.utc)


def grant_premium(db: Session, profile: Profile, plan: Plan) -> datetime:
    """Extends from the current expiry if still active, otherwise from now -
    buying another plan while already premium stacks time rather than
    wasting the remainder."""
    now = datetime.now(timezone.utc)
    base = profile.premium_until if profile.premium_until and profile.premium_until > now else now
    profile.premium_until = base + timedelta(days=plan.duration_days)
    db.flush()
    return profile.premium_until


def mark_paid(db: Session, payment: Payment, razorpay_payment_id: str | None = None, razorpay_signature: str | None = None) -> None:
    if payment.status == "paid":
        return  # idempotent - webhook and client-side verify can both land
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    if razorpay_payment_id:
        payment.razorpay_payment_id = razorpay_payment_id
    if razorpay_signature:
        payment.razorpay_signature = razorpay_signature
    db.flush()
