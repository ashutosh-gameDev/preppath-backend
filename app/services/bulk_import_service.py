"""
CSV / Excel bulk question import: parse -> validate -> preview -> commit.
Nothing is written to the DB until the admin explicitly commits the reviewed
rows (see BulkImportPreview docstring for why no server-side cache is used).
"""
import csv
import io
import uuid

import openpyxl
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course, Subject, Topic
from app.schemas.question import BulkImportDefaults, BulkImportRowError, QuestionCreate

# course/subject are only "always required" when nothing was picked on the
# Upload Paper screen (see BulkImportDefaults) - validate_rows relaxes these
# per-call once defaults cover them, so a paper's file can skip the columns
# entirely.
REQUIRED_COLUMNS = [
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_answer",
]
# course/subject are handled specially in validate_rows (row column OR
# BulkImportDefaults, not a flat required list) - listed here only so the
# frontend's "what columns are optional" copy/template stays accurate.
OPTIONAL_COLUMNS = ["course", "subject", "explanation", "topic", "exam", "year", "difficulty", "type", "source", "tags"]


def _parse_csv(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _parse_xlsx(raw: bytes) -> list[dict]:
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip().lower() if h else "" for h in next(rows_iter)]
    rows = []
    for values in rows_iter:
        if values is None or all(v is None for v in values):
            continue
        rows.append({headers[i]: values[i] for i in range(len(headers)) if i < len(values)})
    return rows


def parse_file(filename: str, raw: bytes) -> list[dict]:
    if filename.lower().endswith(".csv"):
        return _parse_csv(raw)
    if filename.lower().endswith((".xlsx", ".xlsm")):
        return _parse_xlsx(raw)
    raise ValueError("Unsupported file type - upload a .csv or .xlsx file")


def _lookup_cache(db: Session) -> tuple[dict[str, Course], dict[tuple[uuid.UUID, str], Subject], dict[tuple[uuid.UUID, str], Topic]]:
    courses = {c.name.strip().lower(): c for c in db.execute(select(Course)).scalars().all()}
    subjects = {}
    for s in db.execute(select(Subject)).scalars().all():
        subjects[(s.course_id, s.name.strip().lower())] = s
    topics = {}
    for t in db.execute(select(Topic)).scalars().all():
        topics[(t.subject_id, t.name.strip().lower())] = t
    return courses, subjects, topics


def validate_rows(
    db: Session, rows: list[dict], defaults: BulkImportDefaults | None = None
) -> tuple[list[QuestionCreate], list[BulkImportRowError]]:
    defaults = defaults or BulkImportDefaults()
    courses, subjects, topics = _lookup_cache(db)
    valid: list[QuestionCreate] = []
    errors: list[BulkImportRowError] = []

    for i, raw_row in enumerate(rows, start=2):  # row 1 is the header
        row = {(k or "").strip().lower(): (v if v is not None else "") for k, v in raw_row.items()}
        row_errors: list[str] = []

        for col in REQUIRED_COLUMNS:
            if not str(row.get(col, "")).strip():
                row_errors.append(f"Missing required column '{col}'")

        # course/subject: the row's own column wins when present (lets a
        # mixed-course file still work); otherwise fall back to the paper
        # defaults picked once on the Upload Paper screen.
        course = courses.get(str(row.get("course", "")).strip().lower())
        if row.get("course") and course is None:
            row_errors.append(f"Unknown course '{row.get('course')}' - create it in Admin > Courses first")
        if course is None and defaults.course_id:
            course = next((c for c in courses.values() if c.id == defaults.course_id), None)
        if course is None:
            row_errors.append("Missing course - set one on the Upload Paper screen or add a 'course' column")

        subject = None
        if course:
            subject = subjects.get((course.id, str(row.get("subject", "")).strip().lower()))
            if row.get("subject") and subject is None:
                row_errors.append(f"Unknown subject '{row.get('subject')}' for course '{course.name}'")
            if subject is None and defaults.subject_id:
                subject = next((s for s in subjects.values() if s.id == defaults.subject_id), None)
            if subject is None and not row.get("subject"):
                row_errors.append("Missing subject - set one on the Upload Paper screen or add a 'subject' column")

        topic = None
        topic_raw = str(row.get("topic", "")).strip()
        if subject and topic_raw:
            topic = topics.get((subject.id, topic_raw.lower()))
            if topic is None:
                row_errors.append(f"Unknown topic '{topic_raw}' for subject '{subject.name if subject else ''}'")
        elif subject and defaults.topic_id:
            topic = next((t for t in topics.values() if t.id == defaults.topic_id), None)

        if row_errors:
            errors.append(BulkImportRowError(row_number=i, errors=row_errors, raw=row))
            continue

        try:
            year_raw = str(row.get("year", "")).strip()
            exam_raw = str(row.get("exam", "")).strip()
            source_raw = str(row.get("source", "")).strip()
            tags_raw = str(row.get("tags", "")).strip()
            payload = QuestionCreate(
                question_text=str(row["question"]).strip(),
                option_a=str(row["option_a"]).strip(),
                option_b=str(row["option_b"]).strip(),
                option_c=str(row["option_c"]).strip(),
                option_d=str(row["option_d"]).strip(),
                correct_option=str(row["correct_answer"]).strip(),
                explanation=str(row.get("explanation") or "").strip() or None,
                difficulty=(str(row.get("difficulty") or "").strip().lower() or defaults.difficulty or "medium"),
                question_type=(str(row.get("type") or "").strip().lower() or defaults.question_type or "practice"),
                exam_id=_resolve_exam_id(db, exam_raw) if exam_raw else defaults.exam_id,
                year=int(float(year_raw)) if year_raw else defaults.year,
                source=source_raw or defaults.source,
                tags=[t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else [],
                course_id=course.id,
                subject_id=subject.id,
                topic_id=topic.id if topic else None,
            )
            valid.append(payload)
        except (ValidationError, ValueError) as e:
            errors.append(BulkImportRowError(row_number=i, errors=[str(e)], raw=row))

    return valid, errors


def _resolve_exam_id(db: Session, name: str) -> uuid.UUID | None:
    from app.models.exam import Exam

    exam = db.execute(select(Exam).where(Exam.name.ilike(name.strip()))).scalar_one_or_none()
    return exam.id if exam else None
