"""
Refer-a-friend: a student shares their own link (wa.me pre-filled text,
built from referral_code) via WhatsApp. The reward (Pro days) is granted
only once a NEW student actually signs up through that link - not for
merely tapping Share - to avoid a free-Pro loop from tapping the same
button repeatedly. See services/referral_service.py for the claim window
and services/premium_service.grant_premium for the actual tier extension.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import UserTier
from app.models.user import Profile, User
from app.schemas.referral import ReferralClaimRequest, ReferralClaimResult, ReferralMeOut
from app.services import settings_service
from app.services.premium_service import Plan, grant_premium
from app.services.referral_service import can_claim_referral

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("/me", response_model=ReferralMeOut)
def get_my_referral(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reward_days = int(settings_service.get_setting(db, "referral.reward_days"))
    link = f"{settings.STUDENT_WEB_URL}/signup?ref={user.referral_code}"
    referred_count = db.execute(
        select(func.count()).select_from(User).where(User.referred_by == user.id)
    ).scalar_one()
    return ReferralMeOut(
        referral_code=user.referral_code,
        share_text=(
            f"I'm prepping for my exam on PrepPath - join me and get started! {link} "
            f"(we both do better when we study together 😄)"
        ),
        referred_count=referred_count,
        reward_days=reward_days,
    )


@router.post("/claim", response_model=ReferralClaimResult)
def claim_referral(
    payload: ReferralClaimRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Called once by the frontend right after a fresh signup, if a `ref`
    code was captured from the signup URL. Always 200s (never an error) so
    the frontend's fire-and-forget call doesn't need special-case handling -
    `claimed: false` just means nothing happened, for any of several
    legitimate reasons (already claimed, too old, bad code, self-referral)."""
    if not can_claim_referral(user):
        return ReferralClaimResult(claimed=False, detail="This account can no longer claim a referral.")
    referrer = db.execute(select(User).where(User.referral_code == payload.code.strip().upper())).scalar_one_or_none()
    if referrer is None or referrer.id == user.id:
        return ReferralClaimResult(claimed=False, detail="That referral code isn't valid.")

    user.referred_by = referrer.id
    db.flush()
    reward_days = int(settings_service.get_setting(db, "referral.reward_days"))
    referrer_profile = db.get(Profile, referrer.id)
    if referrer_profile is not None:
        plan = Plan(key="referral", label="Referral bonus", amount_paise=0, duration_days=reward_days, tier=UserTier.PRO)
        grant_premium(db, referrer_profile, plan)
    db.flush()
    return ReferralClaimResult(claimed=True, detail=f"Referral recorded - your friend just earned {reward_days} days of Pro!")
