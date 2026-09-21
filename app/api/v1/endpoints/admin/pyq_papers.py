"""
Admin CRUD for `PYQPaper` - the specific PYQ paper tag every question
carries (see models/pyq_paper.py for why this is deliberately not the same
table as `Exam`). Gated on require_content_access (like questions/tests),
not require_admin - content_editor accounts tag papers as part of everyday
question upload.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.pyq_paper import PYQPaper
from app.models.question import Question
from app.models.user import User
from app.schemas.common import Message
from app.schemas.pyq_paper import PYQPaperCreate, PYQPaperOut, PYQPaperUpdate
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/pyq-papers", tags=["admin:pyq-papers"])


def _to_out(paper: PYQPaper, count: int) -> PYQPaperOut:
    return PYQPaperOut(
        id=paper.id, exam_name=paper.exam_name, year=paper.year, label=paper.label, language=paper.language,
        course_id=paper.course_id, is_published=paper.is_published, created_at=paper.created_at, question_count=count,
    )


@router.get("", response_model=list[PYQPaperOut])
def list_pyq_papers(
    course_id: uuid.UUID | None = None,
    search: str | None = None,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    q = select(PYQPaper)
    if course_id:
        q = q.where(PYQPaper.course_id == course_id)
    if search:
        q = q.where(PYQPaper.exam_name.ilike(f"%{search}%"))
    papers = db.execute(q.order_by(PYQPaper.year.desc().nullslast(), PYQPaper.exam_name)).scalars().all()
    if not papers:
        return []

    counts = dict(
        db.execute(
            select(Question.pyq_paper_id, func.count(Question.id))
            .where(Question.pyq_paper_id.in_([p.id for p in papers]))
            .group_by(Question.pyq_paper_id)
        ).all()
    )
    return [_to_out(p, counts.get(p.id, 0)) for p in papers]


@router.post("", response_model=PYQPaperOut)
def create_pyq_paper(payload: PYQPaperCreate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    paper = PYQPaper(**payload.model_dump())
    db.add(paper)
    db.flush()
    log_action(db, admin.id, "create", "pyq_paper", paper.id)
    return _to_out(paper, 0)


@router.patch("/{paper_id}", response_model=PYQPaperOut)
def update_pyq_paper(
    paper_id: uuid.UUID, payload: PYQPaperUpdate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    paper = db.get(PYQPaper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="PYQ paper not found")
    changes = payload.model_dump(exclude_unset=True)
    publish = changes.pop("is_published", None)
    if publish is not None and publish != paper.is_published:
        if admin.role != UserRole.SUPER_ADMIN:
            raise HTTPException(status_code=403, detail="Only a super admin can publish or unpublish a paper.")
        paper.is_published = publish
        log_action(db, admin.id, "publish" if publish else "unpublish", "pyq_paper", paper.id)
    for field, value in changes.items():
        setattr(paper, field, value)
    db.flush()
    if changes:
        log_action(db, admin.id, "update", "pyq_paper", paper.id)
    count = db.execute(select(func.count(Question.id)).where(Question.pyq_paper_id == paper.id)).scalar_one()
    return _to_out(paper, count)


@router.delete("/{paper_id}", response_model=Message)
def delete_pyq_paper(paper_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    paper = db.get(PYQPaper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="PYQ paper not found")
    # Questions tagged to it are NOT deleted (pyq_paper_id just goes NULL via
    # the ON DELETE SET NULL FK) - deleting a paper is a labeling cleanup,
    # never a way to bulk-delete questions.
    db.delete(paper)
    db.flush()
    log_action(db, admin.id, "delete", "pyq_paper", paper_id)
    return Message(detail="PYQ paper deleted")
