"""
Super-admin-managed custom referral/marketing codes (see
models/referral_campaign.py) - e.g. a code printed on a local college
poster, distinct from a student's own auto-generated referral_code.
Claiming one happens through the existing POST /referrals/claim (same
endpoint students already use for peer referral codes); this module is
only the CRM-side management of the codes themselves.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_super_admin
from app.db.session import get_db
from app.models.referral_campaign import ReferralCampaign
from app.models.user import User
from app.schemas.referral_campaign import ReferralCampaignCreate, ReferralCampaignOut, ReferralCampaignUpdate
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/referral-campaigns", tags=["admin:referral-campaigns"])


def _to_out(campaign: ReferralCampaign, signup_count: int) -> ReferralCampaignOut:
    return ReferralCampaignOut(
        id=campaign.id, code=campaign.code, label=campaign.label, reward_days=campaign.reward_days,
        is_active=campaign.is_active, created_at=campaign.created_at, signup_count=signup_count,
    )


@router.get("", response_model=list[ReferralCampaignOut])
def list_campaigns(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Read-only for any admin/content team member (same visibility as the
    rest of /admin/growth) - only creating/editing is super-admin-only."""
    campaigns = db.execute(select(ReferralCampaign).order_by(ReferralCampaign.created_at.desc())).scalars().all()
    if not campaigns:
        return []
    counts = dict(
        db.execute(
            select(User.signup_campaign_id, func.count())
            .where(User.signup_campaign_id.is_not(None))
            .group_by(User.signup_campaign_id)
        ).all()
    )
    return [_to_out(c, counts.get(c.id, 0)) for c in campaigns]


@router.post("", response_model=ReferralCampaignOut)
def create_campaign(
    payload: ReferralCampaignCreate, admin: User = Depends(require_super_admin), db: Session = Depends(get_db)
):
    code = payload.code.strip().upper()
    if not code:
        raise HTTPException(status_code=422, detail="Code is required")
    # One namespace across both kinds of code - a marketing code must never
    # collide with (or shadow) a student's own personal referral code.
    taken = db.execute(select(User.id).where(User.referral_code == code)).first()
    if taken is not None or db.execute(select(ReferralCampaign.id).where(ReferralCampaign.code == code)).first():
        raise HTTPException(status_code=409, detail=f"Code '{code}' is already in use")
    if payload.reward_days < 0:
        raise HTTPException(status_code=422, detail="Reward days can't be negative")

    campaign = ReferralCampaign(code=code, label=payload.label.strip(), reward_days=payload.reward_days, created_by=admin.id)
    db.add(campaign)
    db.flush()
    log_action(db, admin.id, "create", "referral_campaign", campaign.id)
    return _to_out(campaign, 0)


@router.patch("/{campaign_id}", response_model=ReferralCampaignOut)
def update_campaign(
    campaign_id: uuid.UUID,
    payload: ReferralCampaignUpdate,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    campaign = db.get(ReferralCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    changes = payload.model_dump(exclude_unset=True)
    if "reward_days" in changes and changes["reward_days"] is not None and changes["reward_days"] < 0:
        raise HTTPException(status_code=422, detail="Reward days can't be negative")
    for field, value in changes.items():
        setattr(campaign, field, value)
    db.flush()
    if changes:
        log_action(db, admin.id, "update", "referral_campaign", campaign.id)
    count = db.execute(
        select(func.count()).select_from(User).where(User.signup_campaign_id == campaign.id)
    ).scalar_one()
    return _to_out(campaign, count)
