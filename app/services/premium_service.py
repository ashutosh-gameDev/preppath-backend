"""
Premium (ad-free) plans and the logic to grant/extend access after a payment
is confirmed. Amounts are in paise (Razorpay's smallest INR unit, like cents)
- 1 rupee = 100 paise.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.enums import UserTier
from app.models.payment import Payment
from app.models.user import Profile


@dataclass(frozen=True)
class Plan:
    key: str
    label: str
    amount_paise: int
    duration_days: int
    # Which tier a successful purchase of this plan grants - all self-serve
    # plans currently grant PREMIUM; PRO is admin-assigned only for now (see
    # the Users admin page) until a separate self-serve Pro product exists.
    tier: str = UserTier.PREMIUM


PLANS: dict[str, Plan] = {
    "monthly": Plan(key="monthly", label="Monthly", amount_paise=5000, duration_days=30),
    "half_yearly": Plan(key="half_yearly", label="6 Months", amount_paise=25000, duration_days=180),
    "yearly": Plan(key="yearly", label="Yearly", amount_paise=50000, duration_days=365),
}


def get_plan(key: str) -> Plan | None:
    return PLANS.get(key)


def effective_tier(profile: Profile) -> str:
    """`profile.tier` once it lapses back to NORMAL - a stale tier value
    with a past `tier_expires_at` should never keep granting access."""
    if profile.tier == UserTier.NORMAL:
        return UserTier.NORMAL
    if profile.tier_expires_at is None or profile.tier_expires_at <= datetime.now(timezone.utc):
        return UserTier.NORMAL
    return profile.tier


def is_premium(profile: Profile) -> bool:
    """True for either paid tier (Pro or Premium) - both remove ads and lift
    the free 1-course cap; kept named `is_premium` since that's the flag
    both frontends already gate ads/course-limit on. Premium-specific
    behavior (e.g. the future Notes Board sync) should check
    `effective_tier(profile) == UserTier.PREMIUM` directly instead."""
    return effective_tier(profile) != UserTier.NORMAL


def grant_premium(db: Session, profile: Profile, plan: Plan) -> datetime:
    """Extends from the current expiry if still active, otherwise from now -
    buying another plan while already on a paid tier stacks time rather than
    wasting the remainder. Upgrading tiers (e.g. Pro -> Premium) does not
    stack across different tiers - it simply switches `tier` and restarts
    the clock from the greater of "now" and any remaining time."""
    now = datetime.now(timezone.utc)
    still_active = profile.tier_expires_at and profile.tier_expires_at > now
    base = profile.tier_expires_at if still_active else now
    profile.tier = plan.tier
    profile.tier_expires_at = base + timedelta(days=plan.duration_days)
    db.flush()
    return profile.tier_expires_at


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
