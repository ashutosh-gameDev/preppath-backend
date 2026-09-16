"""
Admin CRUD for `JobPosting` - the government/private job vacancy notices
shown on the student Notifications page's Jobs tab. Gated on
require_content_access, same tier as pyq-papers/questions.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.db.session import get_db
from app.models.job_posting import JobPosting
from app.models.user import User
from app.schemas.common import Message
from app.schemas.job_posting import JobPostingCreate, JobPostingOut, JobPostingUpdate
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/job-postings", tags=["admin:job-postings"])


@router.get("", response_model=list[JobPostingOut])
def list_job_postings(
    course_id: uuid.UUID | None = None,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    q = select(JobPosting)
    if course_id:
        q = q.where(JobPosting.course_id == course_id)
    postings = db.execute(q.order_by(JobPosting.posted_date.desc())).scalars().all()
    return postings


@router.post("", response_model=JobPostingOut)
def create_job_posting(
    payload: JobPostingCreate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    posting = JobPosting(**payload.model_dump(), created_by=admin.id)
    db.add(posting)
    db.flush()
    log_action(db, admin.id, "create", "job_posting", posting.id)
    return posting


@router.patch("/{posting_id}", response_model=JobPostingOut)
def update_job_posting(
    posting_id: uuid.UUID,
    payload: JobPostingUpdate,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    posting = db.get(JobPosting, posting_id)
    if posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(posting, field, value)
    db.flush()
    log_action(db, admin.id, "update", "job_posting", posting.id)
    return posting


@router.delete("/{posting_id}", response_model=Message)
def delete_job_posting(
    posting_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    posting = db.get(JobPosting, posting_id)
    if posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    db.delete(posting)
    db.flush()
    log_action(db, admin.id, "delete", "job_posting", posting_id)
    return Message(detail="Job posting deleted")
