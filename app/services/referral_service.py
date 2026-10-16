"""
Refer-a-friend: share your own link via WhatsApp, get Pro once a NEW
student actually signs up through it (not just for tapping Share - see
api/v1/endpoints/referrals.py for why the reward is gated on a real
signup, and deps.py for where referral_code gets assigned).
"""
import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LENGTH = 8
# How long after signup a fresh account can still claim a referral - after
# this window, a stray `ref` code left in the browser's localStorage from
# browsing someone else's share link (without ever signing up through it)
# can no longer retroactively attach itself to an unrelated, already-settled
# account.
CLAIM_WINDOW = timedelta(hours=1)


def generate_unique_referral_code(db: Session) -> str:
    for _ in range(10):
        code = "".join(random.choices(_ALPHABET, k=_CODE_LENGTH))
        exists = db.execute(select(User.id).where(User.referral_code == code)).first()
        if not exists:
            return code
    raise RuntimeError("Could not generate a unique referral code after 10 attempts")


def can_claim_referral(user: User) -> bool:
    if user.referred_by is not None:
        return False
    return datetime.now(timezone.utc) - user.created_at <= CLAIM_WINDOW
