"""Computes an intern's papers-uploaded / earned / paid / remaining summary
- shared by the super-admin view (admin/team.py, any intern) and the
intern's own self-service view (team_self.py, themselves only) so the two
surfaces can never drift apart on how the numbers are derived."""
import uuid

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.admin.questions import IMAGE_FIELDS
from app.models.intern_payment import InternPayment
from app.models.pyq_paper import PYQPaper
from app.models.question import Question
from app.models.user import User
from app.schemas.intern_payment import InternPaperBrief, InternPaymentOut, InternPaymentSummary
from app.services import settings_service


def resolve_rate_paise(db: Session, paper: PYQPaper, image_count: int) -> int:
    """`image_count` is the total filled image slots (question-stem +
    4 option images, summed across every question) on this paper - an
    explicit per-paper `payment_amount_paise` override always wins
    regardless; otherwise a paper needing MORE than
    `intern_payments.image_threshold` images pays the higher
    `intern_payments.high_image_rate_rupees` rate instead of the plain
    default, since papers with lots of pictures to source/crop take real
    extra work beyond typing in the text."""
    if paper.payment_amount_paise is not None:
        return paper.payment_amount_paise
    threshold = int(settings_service.get_setting(db, "intern_payments.image_threshold"))
    if image_count > threshold:
        return int(settings_service.get_setting(db, "intern_payments.high_image_rate_rupees")) * 100
    return int(settings_service.get_setting(db, "intern_payments.default_rate_rupees")) * 100


def compute_summary(db: Session, user_id: uuid.UUID) -> InternPaymentSummary:
    user = db.get(User, user_id)
    default_rate_paise = int(settings_service.get_setting(db, "intern_payments.default_rate_rupees")) * 100

    papers = db.execute(
        select(PYQPaper).where(PYQPaper.created_by == user_id).order_by(PYQPaper.created_at.desc())
    ).scalars().all()
    # Same "sum of filled image slots across every question in the paper"
    # definition admin/pyq_papers.py's own image_count already uses -
    # batched into one query (not one per paper) since resolve_rate_paise
    # needs it for every paper below.
    image_count_expr = sum(func.count(case((getattr(Question, f).isnot(None), 1))) for f in IMAGE_FIELDS)
    image_counts = dict(
        db.execute(
            select(Question.pyq_paper_id, image_count_expr)
            .where(Question.pyq_paper_id.in_([p.id for p in papers]))
            .group_by(Question.pyq_paper_id)
        ).all()
    ) if papers else {}
    paper_briefs = [
        InternPaperBrief(
            id=p.id, exam_name=p.exam_name, year=p.year, label=p.label, created_at=p.created_at,
            amount_paise=resolve_rate_paise(db, p, image_counts.get(p.id, 0)), payment_amount_paise=p.payment_amount_paise,
            image_count=image_counts.get(p.id, 0),
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
