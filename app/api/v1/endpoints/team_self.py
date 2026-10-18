"""A content-editor's (intern's) own read-only view of their papers-
uploaded/earned/paid/remaining summary - deliberately NOT under /admin
(require_super_admin would lock an intern out of their own numbers).
Scoped to the caller's own id regardless of role - harmless for a non-
intern account to call (it just comes back empty)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.intern_payment import InternPaymentSummary
from app.services import intern_payment_service

router = APIRouter(prefix="/team", tags=["team"])


@router.get("/me/payments", response_model=InternPaymentSummary)
def get_my_payments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return intern_payment_service.compute_summary(db, user.id)
