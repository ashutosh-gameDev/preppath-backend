import uuid

from app.schemas.common import ORMModel


class ReferralMeOut(ORMModel):
    referral_code: str
    # Full share text the frontend drops straight into a wa.me link - kept
    # server-side so the wording can change without a frontend redeploy.
    share_text: str
    referred_count: int
    reward_days: int


class ReferralClaimRequest(ORMModel):
    code: str


class ReferralClaimResult(ORMModel):
    claimed: bool
    detail: str
