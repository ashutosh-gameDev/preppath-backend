"""
Admin CRUD for `Paper` - the PYQ/exam paper tag every question carries (see
models/paper.py for why this is deliberately not the same table as `Exam`).
Gated on require_content_access (like questions/tests), not require_admin -
content_editor accounts tag papers as part of everyday question upload.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.db.session import get_db
from app.models.paper import Paper
from app.models.question import Question
from app.models.user import User
from app.schemas.common import Message
from app.schemas.paper import PaperCreate, PaperOut, PaperUpdate
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/papers", tags=["admin:papers"])


def _to_out(paper: Paper, count: int) -> PaperOut:
    return PaperOut(
        id=paper.id, exam_name=paper.exam_name, year=paper.year, label=paper.label, language=paper.language,
        course_id=paper.course_id, created_at=paper.created_at, question_count=count,
    )


@router.get("", response_model=list[PaperOut])
def list_papers(
    course_id: uuid.UUID | None = None,
    search: str | None = None,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    q = select(Paper)
    if course_id:
        q = q.where(Paper.course_id == course_id)
    if search:
        q = q.where(Paper.exam_name.ilike(f"%{search}%"))
    papers = db.execute(q.order_by(Paper.year.desc().nullslast(), Paper.exam_name)).scalars().all()
    if not papers:
        return []

    counts = dict(
        db.execute(
            select(Question.paper_id, func.count(Question.id))
            .where(Question.paper_id.in_([p.id for p in papers]))
            .group_by(Question.paper_id)
        ).all()
    )
    return [_to_out(p, counts.get(p.id, 0)) for p in papers]


@router.post("", response_model=PaperOut)
def create_paper(payload: PaperCreate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    paper = Paper(**payload.model_dump())
    db.add(paper)
    db.flush()
    log_action(db, admin.id, "create", "paper", paper.id)
    return _to_out(paper, 0)


@router.patch("/{paper_id}", response_model=PaperOut)
def update_paper(
    paper_id: uuid.UUID, payload: PaperUpdate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)
    db.flush()
    log_action(db, admin.id, "update", "paper", paper.id)
    count = db.execute(select(func.count(Question.id)).where(Question.paper_id == paper.id)).scalar_one()
    return _to_out(paper, count)


@router.delete("/{paper_id}", response_model=Message)
def delete_paper(paper_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    # Questions tagged to it are NOT deleted (paper_id just goes NULL via the
    # ON DELETE SET NULL FK) - deleting a paper is a labeling cleanup, never
    # a way to bulk-delete questions.
    db.delete(paper)
    db.flush()
    log_action(db, admin.id, "delete", "paper", paper_id)
    return Message(detail="Paper deleted")
