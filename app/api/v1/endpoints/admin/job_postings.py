"""
Admin CRUD for `JobPosting` - the government/private job vacancy notices
shown on the student Notifications page's Jobs tab. Gated on
require_content_access, same tier as pyq-papers/questions.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.db.session import get_db
from app.models.admin import AdminActivityLog
from app.models.job_posting import JobPosting
from app.models.user import User
from app.schemas.common import Message
from app.schemas.job_posting import (
    JobPostingBulkImportRequest,
    JobPostingBulkImportResult,
    JobPostingCreate,
    JobPostingOut,
    JobPostingUpdate,
)
from app.services.admin_log_service import log_action
from app.services.notification_service import notify_eligible_students_for_job

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
    if posting.is_published:
        notify_eligible_students_for_job(db, posting)
    return posting


@router.post("/bulk-import", response_model=JobPostingBulkImportResult)
def bulk_import_job_postings(
    payload: JobPostingBulkImportRequest, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    """Create many postings at once from pasted JSON (see admin-web's Jobs
    page "Import from JSON" flow - an admin pastes a source article into an
    LLM along with a fixed prompt, pastes the JSON reply here). Each
    object is validated the same way a single POST /admin/job-postings
    would be - a malformed one 422s the whole request before anything is
    created, same as any other Pydantic-validated endpoint.

    Batched into two flushes total (not one `log_action` round-trip per
    posting, which also flushes) - a real import can easily be 30-50+
    postings from one article, and each flush is a network round-trip to
    the DB, which for enough postings was slow enough to risk a proxy
    timeout.

    The two flushes are also wrapped so a DB-level failure (e.g. a value
    too long for a column - an LLM asked for a free-text qualification
    routinely writes a full sentence well past what a short dropdown value
    needs) raises a normal HTTPException instead of an unhandled crash.
    That distinction matters here specifically: HTTPException is handled
    by ExceptionMiddleware, which sits INSIDE CORSMiddleware, so the
    response still carries its CORS header; a truly unhandled exception
    escapes to ServerErrorMiddleware, which sits OUTSIDE it, so that
    response has none - the browser then reports a plain 500 as a CORS
    policy violation, which is what actually happened here before this
    import hit a VARCHAR(100) qualification column (see migration 0032)."""
    created: list[JobPosting] = [JobPosting(**item.model_dump(), created_by=admin.id) for item in payload.postings]
    db.add_all(created)
    try:
        db.flush()  # assigns every posting's id in one round trip

        for posting in created:
            db.add(AdminActivityLog(admin_user_id=admin.id, action="create", entity_type="job_posting", entity_id=posting.id))
            if posting.is_published:
                notify_eligible_students_for_job(db, posting)
        db.flush()  # one more round trip for every log row (+ any notifications) together
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Import failed - check the data matches each field: {e}") from e

    return JobPostingBulkImportResult(imported=len(created), postings=created)


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
    was_published = posting.is_published
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(posting, field, value)
    db.flush()
    log_action(db, admin.id, "update", "job_posting", posting.id)
    # Only the draft -> published transition notifies - saving an already-
    # published posting again (e.g. fixing a typo) must never re-notify
    # every eligible student.
    if posting.is_published and not was_published:
        notify_eligible_students_for_job(db, posting)
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
