from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.job_posting import JobPosting
from app.models.user import User
from app.schemas.job_posting import JobPostingOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobPostingOut])
def list_jobs(
    age: int | None = None,
    qualification: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Published job postings, optionally filtered to ones the caller is
    actually eligible for. `age`/`qualification` default to the student's own
    profile (set once from the Jobs tab) when the frontend omits them, but
    the caller can pass either explicitly to preview a different filter -
    a null min_age/max_age/qualification on a posting means "no restriction"
    so it always matches."""
    q = select(JobPosting).where(JobPosting.is_published.is_(True))
    if age is not None:
        q = q.where(
            or_(JobPosting.min_age.is_(None), JobPosting.min_age <= age),
            or_(JobPosting.max_age.is_(None), JobPosting.max_age >= age),
        )
    if qualification:
        q = q.where(or_(JobPosting.qualification.is_(None), JobPosting.qualification.ilike(qualification)))
    return db.execute(q.order_by(JobPosting.posted_date.desc())).scalars().all()
