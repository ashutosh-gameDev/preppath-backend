"""
Admin CRUD for `PYQPaper` - the specific PYQ paper tag every question
carries (see models/pyq_paper.py for why this is deliberately not the same
table as `Exam`). Gated on require_content_access (like questions/tests),
not require_admin - content_editor accounts tag papers as part of everyday
question upload.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session

from app.api.deps import require_content_access
from app.api.v1.endpoints.admin.questions import IMAGE_FIELDS
from app.db.session import get_db
from app.models.enums import ContentStatus, UserRole
from app.models.pyq_paper import PYQPaper
from app.models.question import Question
from app.models.user import User
from app.schemas.common import Message
from app.schemas.pyq_paper import PYQPaperCreate, PYQPaperOut, PYQPaperPreviewOut, PYQPaperUpdate
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/pyq-papers", tags=["admin:pyq-papers"])


def _scope_own(q, admin: User):
    """Same ownership rule as admin/questions.py's _scope_own: a team member
    only sees/touches papers they created themselves - only super_admin sees
    every paper."""
    if admin.role != UserRole.SUPER_ADMIN:
        q = q.where(PYQPaper.created_by == admin.id)
    return q


def _require_owned(paper: PYQPaper | None, admin: User) -> PYQPaper:
    """Same rule as _scope_own, for the single-row endpoints that fetch by id
    directly - 404 (not 403) so a non-owner can't tell whether the id exists."""
    if paper is None or (admin.role != UserRole.SUPER_ADMIN and paper.created_by != admin.id):
        raise HTTPException(status_code=404, detail="PYQ paper not found")
    return paper


def publish_paper_questions(db: Session, paper_id: uuid.UUID) -> int:
    """Publishing a paper is meant to make it (and everything in it) visible
    to students - a paper whose questions were still sitting in Draft would
    quietly exclude them from ordinary Practice/stats even though PYQ itself
    already shows them. Only flips DRAFT -> PUBLISHED; a question someone
    archived on purpose is left alone. Returns how many were switched."""
    result = db.execute(
        update(Question)
        .where(Question.pyq_paper_id == paper_id, Question.status == ContentStatus.DRAFT)
        .values(status=ContentStatus.PUBLISHED)
    )
    return result.rowcount or 0


def _to_out(paper: PYQPaper, count: int, needs_image_count: int = 0, image_count: int = 0) -> PYQPaperOut:
    return PYQPaperOut(
        id=paper.id, exam_name=paper.exam_name, year=paper.year, label=paper.label, language=paper.language,
        course_id=paper.course_id, is_published=paper.is_published, created_at=paper.created_at, question_count=count,
        needs_image_count=needs_image_count, uploaded_by=paper.uploaded_by, created_by=paper.created_by,
        image_count=image_count, max_marks=paper.max_marks, time_limit_minutes=paper.time_limit_minutes,
        marks_per_question=paper.marks_per_question, negative_marking=paper.negative_marking,
        payment_amount_paise=paper.payment_amount_paise,
    )


@router.get("", response_model=list[PYQPaperOut])
def list_pyq_papers(
    course_id: uuid.UUID | None = None,
    search: str | None = None,
    is_published: bool | None = None,
    year: int | None = None,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    q = select(PYQPaper)
    if course_id:
        q = q.where(PYQPaper.course_id == course_id)
    if search:
        q = q.where(or_(PYQPaper.exam_name.ilike(f"%{search}%"), PYQPaper.label.ilike(f"%{search}%")))
    if is_published is not None:
        q = q.where(PYQPaper.is_published.is_(is_published))
    if year is not None:
        q = q.where(PYQPaper.year == year)
    q = _scope_own(q, admin)
    papers = db.execute(q.order_by(PYQPaper.year.desc().nullslast(), PYQPaper.exam_name)).scalars().all()
    if not papers:
        return []

    paper_ids = [p.id for p in papers]
    counts = dict(
        db.execute(
            select(Question.pyq_paper_id, func.count(Question.id))
            .where(Question.pyq_paper_id.in_(paper_ids))
            .group_by(Question.pyq_paper_id)
        ).all()
    )
    needs_image_counts = dict(
        db.execute(
            select(Question.pyq_paper_id, func.count(Question.id))
            .where(Question.pyq_paper_id.in_(paper_ids), Question.needs_image.is_(True))
            .group_by(Question.pyq_paper_id)
        ).all()
    )
    # Sum, across the 5 image slots, how many questions in each paper have
    # that slot filled - func.count(case(...)) only counts rows where the
    # case evaluates non-null, so each term below is "how many questions in
    # this paper have this one image field set", summed into one number.
    image_count_expr = sum(func.count(case((getattr(Question, f).isnot(None), 1))) for f in IMAGE_FIELDS)
    image_counts = dict(
        db.execute(
            select(Question.pyq_paper_id, image_count_expr)
            .where(Question.pyq_paper_id.in_(paper_ids))
            .group_by(Question.pyq_paper_id)
        ).all()
    )
    return [
        _to_out(p, counts.get(p.id, 0), needs_image_counts.get(p.id, 0), image_counts.get(p.id, 0)) for p in papers
    ]


@router.get("/for-preview", response_model=list[PYQPaperOut])
def list_pyq_papers_for_preview(
    course_id: uuid.UUID | None = None,
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    """Every paper regardless of who created it - populates the paper picker
    on the cross-team Preview page. Unlike GET /admin/pyq-papers (which
    scopes non-super-admins to their own papers to keep in-progress upload
    work separate), reviewing finished content is deliberately everyone's
    job, not just the uploader's, so this one is never scoped by created_by."""
    q = select(PYQPaper)
    if course_id:
        q = q.where(PYQPaper.course_id == course_id)
    papers = db.execute(q.order_by(PYQPaper.year.desc().nullslast(), PYQPaper.exam_name)).scalars().all()
    if not papers:
        return []
    paper_ids = [p.id for p in papers]
    counts = dict(
        db.execute(
            select(Question.pyq_paper_id, func.count(Question.id))
            .where(Question.pyq_paper_id.in_(paper_ids))
            .group_by(Question.pyq_paper_id)
        ).all()
    )
    return [_to_out(p, counts.get(p.id, 0)) for p in papers]


@router.get("/{paper_id}/preview", response_model=PYQPaperPreviewOut)
def preview_pyq_paper(paper_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    """The whole paper exactly as the cross-team Preview page renders it -
    every question regardless of who created it (not just the admin's own),
    in the same order students see them in the attempt screen."""
    paper = db.get(PYQPaper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="PYQ paper not found")
    questions = db.execute(
        select(Question).where(Question.pyq_paper_id == paper_id).order_by(Question.display_number)
    ).scalars().all()
    needs_image_count = sum(1 for q in questions if q.needs_image)
    image_count = sum(1 for q in questions for f in IMAGE_FIELDS if getattr(q, f))
    return PYQPaperPreviewOut(
        paper=_to_out(paper, len(questions), needs_image_count, image_count), questions=questions
    )


def _find_duplicate(
    db: Session, exam_name: str, year: int | None, label: str | None, language: str | None
) -> PYQPaper | None:
    """Same identity rule bulk_import_service's paper cache already uses
    (exam_name + year + label + language, case-insensitive) - checked across
    every uploader's papers, not just the caller's own (unlike _scope_own),
    so two interns independently creating "the same paper" land on one row
    instead of two silent duplicates neither can see the other made.
    `language` is part of the identity (not just a descriptive field) because
    some exams (RRB JE, UP Police, etc.) release the English and Hindi paper
    as two separate PDFs - those need two separate PYQPaper rows, not one
    paper silently holding both languages' questions under whichever
    language got uploaded first."""
    norm_label = (label or "").strip().lower() or None
    norm_language = (language or "").strip().lower() or None
    year_clause = PYQPaper.year.is_(None) if year is None else PYQPaper.year == year
    candidates = db.execute(
        select(PYQPaper).where(func.lower(PYQPaper.exam_name) == exam_name.strip().lower(), year_clause)
    ).scalars().all()
    for p in candidates:
        if ((p.label or "").strip().lower() or None) == norm_label and ((p.language or "").strip().lower() or None) == norm_language:
            return p
    return None


@router.post("", response_model=PYQPaperOut)
def create_pyq_paper(payload: PYQPaperCreate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    existing = _find_duplicate(db, payload.exam_name, payload.year, payload.label, payload.language)
    if existing is not None:
        count = db.execute(select(func.count(Question.id)).where(Question.pyq_paper_id == existing.id)).scalar_one()
        return _to_out(existing, count)
    paper = PYQPaper(**payload.model_dump(), created_by=admin.id)
    db.add(paper)
    db.flush()
    log_action(db, admin.id, "create", "pyq_paper", paper.id)
    return _to_out(paper, 0)


@router.patch("/{paper_id}", response_model=PYQPaperOut)
def update_pyq_paper(
    paper_id: uuid.UUID, payload: PYQPaperUpdate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)
):
    paper = _require_owned(db.get(PYQPaper, paper_id), admin)
    changes = payload.model_dump(exclude_unset=True)
    if "payment_amount_paise" in changes and admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only a super admin can set a paper's payment amount.")
    publish = changes.pop("is_published", None)
    if publish is not None and publish != paper.is_published:
        if admin.role != UserRole.SUPER_ADMIN:
            raise HTTPException(status_code=403, detail="Only a super admin can publish or unpublish a paper.")
        paper.is_published = publish
        extra = None
        if publish:
            # Only the draft -> published transition cascades, same rule as
            # publishing a course - saving an already-published paper never
            # re-publishes a question someone deliberately archived.
            published_count = publish_paper_questions(db, paper.id)
            if published_count:
                extra = {"published_questions": published_count}
        log_action(db, admin.id, "publish" if publish else "unpublish", "pyq_paper", paper.id, extra)
    for field, value in changes.items():
        setattr(paper, field, value)
    db.flush()
    if changes:
        log_action(db, admin.id, "update", "pyq_paper", paper.id)
    count = db.execute(select(func.count(Question.id)).where(Question.pyq_paper_id == paper.id)).scalar_one()
    needs_image_count = db.execute(
        select(func.count(Question.id)).where(Question.pyq_paper_id == paper.id, Question.needs_image.is_(True))
    ).scalar_one()
    image_count_expr = sum(func.count(case((getattr(Question, f).isnot(None), 1))) for f in IMAGE_FIELDS)
    image_count = db.execute(select(image_count_expr).where(Question.pyq_paper_id == paper.id)).scalar_one() or 0
    return _to_out(paper, count, needs_image_count, image_count)


@router.delete("/{paper_id}", response_model=Message)
def delete_pyq_paper(paper_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    paper = _require_owned(db.get(PYQPaper, paper_id), admin)
    if paper.is_published and admin.role == UserRole.CONTENT_EDITOR:
        raise HTTPException(status_code=403, detail="Only an admin can delete a published PYQ paper")
    # Questions tagged to it are NOT deleted (pyq_paper_id just goes NULL via
    # the ON DELETE SET NULL FK) - deleting a paper is a labeling cleanup,
    # never a way to bulk-delete questions.
    db.delete(paper)
    db.flush()
    log_action(db, admin.id, "delete", "pyq_paper", paper_id)
    return Message(detail="PYQ paper deleted")
