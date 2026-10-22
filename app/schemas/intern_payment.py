import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class InternPaymentCreate(ORMModel):
    amount_paise: int
    note: str | None = None


class InternPaymentOut(ORMModel):
    id: uuid.UUID
    amount_paise: int
    note: str | None
    paid_at: datetime
    created_by_name: str | None = None


class InternPaperBrief(ORMModel):
    """One paper's contribution to the summary below - `amount_paise` is
    already resolved (the paper's own override, or the platform default)."""
    id: uuid.UUID
    exam_name: str
    year: int | None
    label: str | None
    created_at: datetime
    amount_paise: int
    # The paper's own override, if any - null here (even though
    # amount_paise above is never null) means this row is currently priced
    # at the platform default rate, not a paper-specific one.
    payment_amount_paise: int | None
    # Why amount_paise came out the way it did - shown alongside it so an
    # admin can tell "high-image rate" from "plain default" at a glance,
    # without having to check the question images themselves.
    image_count: int


class InternPaymentSummary(ORMModel):
    user_id: uuid.UUID
    username: str | None = None
    papers: list[InternPaperBrief]
    papers_uploaded: int
    default_rate_paise: int
    total_earned_paise: int
    total_paid_paise: int
    remaining_paise: int
    payments: list[InternPaymentOut]
