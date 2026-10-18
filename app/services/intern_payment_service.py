"""Computes an intern's papers-uploaded / earned / paid / remaining summary
- shared by the super-admin view (admin/team.py, any intern) and the
intern's own self-service view (team_self.py, themselves only) so the two
surfaces can never drift apart on how the numbers are derived."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.intern_payment import InternPayment
from app.models.pyq_paper import PYQPaper
from app.models.user import User
from app.schemas.intern_payment import InternPaperBrief, InternPaymentOut, InternPaymentSummary
from app.services import settings_service


def resolve_rate_paise(db: Session, paper: PYQPaper) -> int:
    if paper.payment_amount_paise is not None:
        return paper.payment_amount_paise
    return int(settings_service.get_setting(db, "intern_payments.default_rate_rupees")) * 100


def compute_summary(db: Session, user_id: uuid.UUID) -> InternPaymentSummary:
    user = db.get(User, user_id)
    default_rate_paise = int(settings_service.get_setting(db, "intern_payments.default_rate_rupees")) * 100

    papers = db.execute(
        select(PYQPaper).where(PYQPaper.created_by == user_id).order_by(PYQPaper.created_at.desc())
    ).scalars().all()
    paper_briefs = [
        InternPaperBrief(
            id=p.id, exam_name=p.exam_name, year=p.year, label=p.label, created_at=p.created_at,
            amount_paise=resolve_rate_paise(db, p), payment_amount_paise=p.payment_amount_paise,
        )
        for p in papers
    ]
    total_earned_paise = sum(p.amount_paise for p in paper_briefs)

    payment_rows = db.execute(
        select(InternPayment, User.username, User.full_name)
        .outerjoin(User, User.id == InternPayment.created_by)
        .where(InternPayment.user_id == user_id)
        .order_by(InternPayment.paid_at.desc())
    ).all()
    payments = [
        InternPaymentOut(
            id=payment.id, amount_paise=payment.amount_paise, note=payment.note, paid_at=payment.paid_at,
            created_by_name=username or full_name,
        )
        for payment, username, full_name in payment_rows
    ]
    total_paid_paise = sum(p.amount_paise for p in payments)

    return InternPaymentSummary(
        user_id=user_id, username=user.username if user else None,
        papers=paper_briefs, papers_uploaded=len(paper_briefs), default_rate_paise=default_rate_paise,
        total_earned_paise=total_earned_paise, total_paid_paise=total_paid_paise,
        remaining_paise=total_earned_paise - total_paid_paise, payments=payments,
    )
