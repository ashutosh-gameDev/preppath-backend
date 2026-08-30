"""Raw attempt-history access + question reporting. Most read paths students
actually use go through `statistics.py` (aggregated); this exposes the raw
ledger for things like an activity log, and the 'Report Question' action."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.admin import Report
from app.models.attempt import Attempt
from app.models.user import User
from app.schemas.attempt import AttemptOut
from app.schemas.common import Message
from app.schemas.question import ReportQuestionRequest

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.get("", response_model=list[AttemptOut])
def list_my_attempts(limit: int = 50, offset: int = 0, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.execute(
        select(Attempt)
        .where(Attempt.user_id == user.id)
        .order_by(Attempt.attempted_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()


@router.post("/report", response_model=Message)
def report_question(payload: ReportQuestionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(
        Report(
            user_id=user.id,
            question_id=payload.question_id,
            reason=payload.reason,
            description=payload.description,
        )
    )
    db.flush()
    return Message(detail="Report submitted. Thank you.")
