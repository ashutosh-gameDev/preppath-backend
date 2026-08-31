import json
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_content_access
from app.db.session import get_db
from app.models.admin import Report
from app.models.question import Question, Tag
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.question import (
    BulkImportCommitRequest,
    BulkImportCommitResult,
    BulkImportDefaults,
    BulkImportPreview,
    QuestionAdminOut,
    QuestionCreate,
    QuestionUpdate,
)
from app.services import bulk_import_service, storage_service
from app.services.admin_log_service import log_action

router = APIRouter(prefix="/admin/questions", tags=["admin:questions"])


def _get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    tags = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


@router.get("", response_model=Page[QuestionAdminOut])
def list_questions(
    course_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    topic_id: uuid.UUID | None = None,
    exam_id: uuid.UUID | None = None,
    year: int | None = None,
    source: str | None = None,
    language: str | None = None,
    difficulty: str | None = None,
    question_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    display_number: int | None = Query(None, description="Exact match on the short question # (e.g. 1042)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    q = select(Question)
    if course_id:
        q = q.where(Question.course_id == course_id)
    if subject_id:
        q = q.where(Question.subject_id == subject_id)
    if topic_id:
        q = q.where(Question.topic_id == topic_id)
    if exam_id:
        q = q.where(Question.exam_id == exam_id)
    if year:
        q = q.where(Question.year == year)
    if source:
        q = q.where(Question.source == source)
    if language:
        q = q.where(Question.language == language)
    if difficulty:
        q = q.where(Question.difficulty == difficulty)
    if question_type:
        q = q.where(Question.question_type == question_type)
    if status:
        q = q.where(Question.status == status)
    if display_number:
        q = q.where(Question.display_number == display_number)
    if search:
        q = q.where(Question.question_text.ilike(f"%{search}%"))

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    items = db.execute(
        q.order_by(Question.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return Page.build(items, total, page, page_size)


@router.get("/papers")
def list_papers(admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    """Distinct (exam, year, source) groups among tagged questions - powers
    the 'load questions from a PYQ paper' picker in the test builder, and the
    paper filter in the questions list. A question only counts as belonging
    to a paper once exam + year + source are ALL set."""
    from app.models.exam import Exam

    rows = db.execute(
        select(Question.exam_id, Exam.name, Question.year, Question.source, Question.language, func.count(Question.id))
        .join(Exam, Exam.id == Question.exam_id)
        .where(Question.exam_id.isnot(None), Question.year.isnot(None), Question.source.isnot(None))
        .group_by(Question.exam_id, Exam.name, Question.year, Question.source, Question.language)
        .order_by(Question.year.desc(), Exam.name)
    ).all()
    return [
        {"exam_id": r[0], "exam_name": r[1], "year": r[2], "source": r[3], "language": r[4], "question_count": r[5]}
        for r in rows
    ]


@router.get("/{question_id}", response_model=QuestionAdminOut)
def get_question(question_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.post("", response_model=QuestionAdminOut)
def create_question(payload: QuestionCreate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"tags"})
    question = Question(**data, created_by=admin.id)
    question.tags = _get_or_create_tags(db, payload.tags)
    db.add(question)
    db.flush()
    log_action(db, admin.id, "create", "question", question.id)
    return question


@router.patch("/{question_id}", response_model=QuestionAdminOut)
def update_question(question_id: uuid.UUID, payload: QuestionUpdate, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    data = payload.model_dump(exclude_unset=True, exclude={"tags"})
    for field, value in data.items():
        setattr(question, field, value)
    if payload.tags is not None:
        question.tags = _get_or_create_tags(db, payload.tags)
    db.flush()
    log_action(db, admin.id, "update", "question", question.id)
    return question


@router.delete("/{question_id}", response_model=Message)
def delete_question(question_id: uuid.UUID, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.flush()
    log_action(db, admin.id, "delete", "question", question_id)
    return Message(detail="Question deleted")


# --- Image upload ---------------------------------------------------------------

@router.post("/upload-image")
async def upload_question_image(file: UploadFile, admin: User = Depends(require_content_access)):
    content = await file.read()
    try:
        url = storage_service.upload_question_image(content, file.filename or "image.jpg", file.content_type or "")
    except storage_service.UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"url": url}


# --- Bulk import ---------------------------------------------------------------

def _parse_defaults(defaults: str | None) -> BulkImportDefaults:
    """`defaults` is a JSON-encoded BulkImportDefaults sent as a form field
    alongside the file (multipart requests can't carry a nested JSON body) -
    it's the paper-level Course/Subject/Topic/Exam/Year/Paper-label filled in
    once on the Upload Paper screen and applied to every row that doesn't
    specify its own value."""
    if not defaults:
        return BulkImportDefaults()
    try:
        return BulkImportDefaults.model_validate(json.loads(defaults))
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid paper defaults: {e}")


@router.post("/bulk-import/preview", response_model=BulkImportPreview)
async def bulk_import_preview(
    file: UploadFile,
    defaults: str | None = Form(None),
    admin: User = Depends(require_content_access),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    try:
        rows = bulk_import_service.parse_file(file.filename or "", raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    valid, errors = bulk_import_service.validate_rows(db, rows, _parse_defaults(defaults))
    return BulkImportPreview(
        total_rows=len(rows), valid_count=len(valid), invalid_count=len(errors), errors=errors, valid_rows=valid
    )


@router.post("/bulk-import/commit", response_model=BulkImportCommitResult)
def bulk_import_commit(payload: BulkImportCommitRequest, admin: User = Depends(require_content_access), db: Session = Depends(get_db)):
    imported = 0
    for row in payload.rows:
        # `data` already carries status="draft" (QuestionCreate's field
        # default - bulk-import rows never set it otherwise), so it must NOT
        # also be passed explicitly below - Question() would get 'status'
        # twice and raise TypeError on every single commit.
        data = row.model_dump(exclude={"tags"})
        question = Question(**data, created_by=admin.id)
        question.tags = _get_or_create_tags(db, row.tags)
        db.add(question)
        imported += 1
    db.flush()
    log_action(db, admin.id, "bulk_import", "question", extra={"imported": imported})
    return BulkImportCommitResult(imported=imported, skipped=0)


# --- Reports --------------------------------------------------------------------

@router.get("/reports/list")
def list_reports(status: str | None = None, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = select(Report)
    if status:
        q = q.where(Report.status == status)
    return db.execute(q.order_by(Report.created_at.desc())).scalars().all()


@router.patch("/reports/{report_id}", response_model=Message)
def update_report(report_id: uuid.UUID, status: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = status
    report.reviewed_by = admin.id
    db.flush()
    return Message(detail="Report updated")
