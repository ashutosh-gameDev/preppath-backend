"""
Premium (ad-free) subscription purchase, via Razorpay.

Order creation and signature verification are done with plain HTTP calls
(httpx) against Razorpay's REST API rather than pulling in their SDK - it's
a handful of well-documented calls, not worth an extra dependency.

Local development without a Razorpay account: if RAZORPAY_KEY_ID/SECRET
aren't set AND the backend is running with ENVIRONMENT=development, checkout
returns `dev_mode=True` and the frontend calls `/premium/dev-complete`
instead of opening the real Razorpay checkout - same end state (a `paid`
Payment row, extended `premium_until`), no real payment gateway involved.
This is hard-disabled in any other environment (see `_dev_mode_allowed`).
"""
import hashlib
import hmac
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_profile, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.payment import Payment
from app.models.user import Profile, User
from app.schemas.premium import (
    CheckoutRequest,
    CheckoutResponse,
    DevCompleteRequest,
    PlanOut,
    PremiumStatusOut,
    VerifyRequest,
)
from app.services import premium_service

router = APIRouter(prefix="/premium", tags=["premium"])

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"


def _plans_out() -> list[PlanOut]:
    return [
        PlanOut(key=p.key, label=p.label, amount_paise=p.amount_paise, amount_rupees=p.amount_paise / 100, duration_days=p.duration_days)
        for p in premium_service.PLANS.values()
    ]


def _razorpay_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def _dev_mode_allowed() -> bool:
    return settings.ENVIRONMENT.lower() == "development" and not _razorpay_configured()


@router.get("/status", response_model=PremiumStatusOut)
def get_status(profile: Profile = Depends(get_current_active_profile)):
    return PremiumStatusOut(
        is_premium=premium_service.is_premium(profile),
        premium_until=profile.premium_until,
        plans=_plans_out(),
    )


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = premium_service.get_plan(payload.plan)
    if plan is None:
        raise HTTPException(status_code=400, detail="Unknown plan")

    payment = Payment(user_id=user.id, plan=plan.key, amount_paise=plan.amount_paise, status="created")
    db.add(payment)
    db.flush()

    if _razorpay_configured():
        try:
            resp = httpx.post(
                RAZORPAY_ORDERS_URL,
                json={"amount": plan.amount_paise, "currency": "INR", "receipt": str(payment.id), "payment_capture": 1},
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                timeout=15,
            )
            resp.raise_for_status()
            order = resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Could not reach Razorpay: {e}")
        payment.razorpay_order_id = order["id"]
        db.flush()
        return CheckoutResponse(
            payment_id=payment.id,
            dev_mode=False,
            razorpay_order_id=order["id"],
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
            amount_paise=plan.amount_paise,
            plan=plan.key,
        )

    if not _dev_mode_allowed():
        raise HTTPException(status_code=500, detail="Payments are not configured on this server")

    return CheckoutResponse(payment_id=payment.id, dev_mode=True, amount_paise=plan.amount_paise, plan=plan.key)


@router.post("/dev-complete", response_model=PremiumStatusOut)
def dev_complete(
    payload: DevCompleteRequest,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    if not _dev_mode_allowed():
        raise HTTPException(status_code=404, detail="Not found")

    payment = db.get(Payment, payload.payment_id)
    if payment is None or payment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Payment not found")
    plan = premium_service.get_plan(payment.plan)
    if plan is None:
        raise HTTPException(status_code=400, detail="Unknown plan on payment")

    premium_service.mark_paid(db, payment)
    premium_service.grant_premium(db, profile, plan)

    return PremiumStatusOut(is_premium=True, premium_until=profile.premium_until, plans=_plans_out())


@router.post("/verify", response_model=PremiumStatusOut)
def verify(
    payload: VerifyRequest,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_current_active_profile),
    db: Session = Depends(get_db),
):
    if not _razorpay_configured():
        raise HTTPException(status_code=500, detail="Payments are not configured on this server")

    payment = db.get(Payment, payload.payment_id)
    if payment is None or payment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.razorpay_order_id != payload.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Order mismatch")

    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Signature verification failed")

    plan = premium_service.get_plan(payment.plan)
    premium_service.mark_paid(db, payment, payload.razorpay_payment_id, payload.razorpay_signature)
    if plan:
        premium_service.grant_premium(db, profile, plan)

    return PremiumStatusOut(is_premium=premium_service.is_premium(profile), premium_until=profile.premium_until, plans=_plans_out())


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Razorpay server-to-server confirmation - the reliable path if the
    student closes their browser right after paying, before the client-side
    `/verify` call fires. Configure this URL + a webhook secret in the
    Razorpay dashboard; safe to leave unconfigured (unreachable) locally.
    """
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=404, detail="Not found")

    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = await request.json()
    if payload.get("event") != "payment.captured":
        return {"status": "ignored"}

    order_id = payload["payload"]["payment"]["entity"]["order_id"]
    razorpay_payment_id = payload["payload"]["payment"]["entity"]["id"]

    payment = db.execute(select(Payment).where(Payment.razorpay_order_id == order_id)).scalar_one_or_none()
    if payment is None:
        return {"status": "unknown_order"}

    plan = premium_service.get_plan(payment.plan)
    premium_service.mark_paid(db, payment, razorpay_payment_id)
    if plan:
        profile = db.get(Profile, payment.user_id)
        if profile:
            premium_service.grant_premium(db, profile, plan)

    return {"status": "ok"}
