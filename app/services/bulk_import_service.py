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

from app.models.course import Course, Subject, Subtopic, Topic
from app.models.pyq_paper import PYQPaper
from app.schemas.question import BulkImportDefaults, BulkImportRowError, QuestionCreate

# course/subject/paper are only "always required" when nothing was picked on
# the Upload Paper screen (see BulkImportDefaults) - validate_rows relaxes
# these per-call once defaults cover them, so a paper's file can skip the
# columns entirely. option_a-d are only required when the row's format is
# mcq (the default) - a fill_blank row needs just question + correct_answer.
REQUIRED_COLUMNS = ["question", "correct_answer"]
MCQ_REQUIRED_COLUMNS = ["option_a", "option_b", "option_c", "option_d"]
FORMAT_VALUES = {"mcq", "fill_blank"}
# course/subject/paper are handled specially in validate_rows (row column(s)
# OR BulkImportDefaults, not a flat required list) - listed here only so the
# frontend's "what columns are optional" copy/template stays accurate.
OPTIONAL_COLUMNS = [
    "course", "subject", "explanation", "topic", "subtopic", "exam", "year", "difficulty",
    "type", "source", "language", "tags", "format",
]


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


def _lookup_cache(
    db: Session,
) -> tuple[
    dict[str, Course], dict[tuple[uuid.UUID, str], Subject], dict[tuple[uuid.UUID, str], Topic],
    dict[tuple[uuid.UUID, str], Subtopic], dict[tuple[str, int | None, str | None], PYQPaper],
]:
    courses = {c.name.strip().lower(): c for c in db.execute(select(Course)).scalars().all()}
    subjects = {}
    for s in db.execute(select(Subject)).scalars().all():
        subjects[(s.course_id, s.name.strip().lower())] = s
    topics = {}
    for t in db.execute(select(Topic)).scalars().all():
        topics[(t.subject_id, t.name.strip().lower())] = t
    subtopics = {}
    for st in db.execute(select(Subtopic)).scalars().all():
        subtopics[(st.topic_id, st.name.strip().lower())] = st
    papers = {}
    for p in db.execute(select(PYQPaper)).scalars().all():
        papers[(p.exam_name.strip().lower(), p.year, (p.label or "").strip().lower() or None)] = p
    return courses, subjects, topics, subtopics, papers


def validate_rows(
    db: Session, rows: list[dict], defaults: BulkImportDefaults | None = None
) -> tuple[list[QuestionCreate], list[BulkImportRowError]]:
    defaults = defaults or BulkImportDefaults()
    courses, subjects, topics, subtopics, papers = _lookup_cache(db)
    valid: list[QuestionCreate] = []
    errors: list[BulkImportRowError] = []

    for i, raw_row in enumerate(rows, start=2):  # row 1 is the header
        row = {(k or "").strip().lower(): (v if v is not None else "") for k, v in raw_row.items()}
        row_errors: list[str] = []

        format_raw = str(row.get("format") or row.get("question_format") or "").strip().lower()
        question_format = format_raw if format_raw in FORMAT_VALUES else "mcq"

        for col in REQUIRED_COLUMNS:
            if not str(row.get(col, "")).strip():
                row_errors.append(f"Missing required column '{col}'")
        if question_format == "mcq":
            for col in MCQ_REQUIRED_COLUMNS:
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

        # subtopic ("topic" in product vocabulary, one level finer than
        # `topic` above which is "chapter") - only resolvable once a topic is
        # known, since a subtopic name is only unique within its topic.
        subtopic = None
        subtopic_raw = str(row.get("subtopic", "")).strip()
        if topic and subtopic_raw:
            subtopic = subtopics.get((topic.id, subtopic_raw.lower()))
            if subtopic is None:
                row_errors.append(f"Unknown subtopic '{subtopic_raw}' for topic '{topic.name}'")
        elif topic and defaults.subtopic_id:
            candidate = next((st for st in subtopics.values() if st.id == defaults.subtopic_id), None)
            # Only apply the paper-level default subtopic if it actually
            # belongs to this row's resolved topic - otherwise silently
            # leave it unset rather than cross-wiring an unrelated chapter.
            subtopic = candidate if candidate and candidate.topic_id == topic.id else None

        # pyq_paper: the row's own exam/year/source columns win when present.
        # Unlike topic/subtopic above (which error on an unmatched name - a
        # likely typo against a fixed syllabus), an unmatched exam/year/
        # source auto-creates a new PYQPaper: bulk files are commonly the
        # FIRST time a given paper's name is typed anywhere, so forcing a
        # separate "create the paper, then re-upload" round trip is pure
        # friction. Cached in `papers` so every row in this same file for the
        # same exam/year/source reuses the one paper instead of creating a
        # duplicate per row.
        pyq_paper_id: uuid.UUID | None = None
        exam_raw = str(row.get("exam", "")).strip()
        year_raw = str(row.get("year", "")).strip()
        source_raw = str(row.get("source", "")).strip()
        if exam_raw:
            try:
                paper_year = int(float(year_raw)) if year_raw else None
            except ValueError:
                paper_year = None
            cache_key = (exam_raw.lower(), paper_year, source_raw.lower() or None)
            paper = papers.get(cache_key)
            if paper is None:
                paper = PYQPaper(
                    exam_name=exam_raw, year=paper_year, label=source_raw or None,
                    course_id=course.id if course else defaults.course_id,
                )
                db.add(paper)
                db.flush()
                papers[cache_key] = paper
            pyq_paper_id = paper.id
        elif defaults.pyq_paper_id:
            pyq_paper_id = defaults.pyq_paper_id
        else:
            row_errors.append("Missing PYQ paper - pick one on the Upload Paper screen or add an 'exam' column")

        if row_errors:
            errors.append(BulkImportRowError(row_number=i, errors=row_errors, raw=row))
            continue

        try:
            language_raw = str(row.get("language", "")).strip()
            tags_raw = str(row.get("tags", "")).strip()
            common = dict(
                question_text=str(row["question"]).strip(),
                explanation=str(row.get("explanation") or "").strip() or None,
                difficulty=(str(row.get("difficulty") or "").strip().lower() or defaults.difficulty or "medium"),
                question_type=(str(row.get("type") or "").strip().lower() or defaults.question_type or "practice"),
                pyq_paper_id=pyq_paper_id,
                language=language_raw or defaults.language,
                tags=[t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else [],
                course_id=course.id,
                subject_id=subject.id,
                topic_id=topic.id if topic else None,
                subtopic_id=subtopic.id if subtopic else None,
            )
            if question_format == "mcq":
                payload = QuestionCreate(
                    **common,
                    question_format="mcq",
                    option_a=str(row["option_a"]).strip(),
                    option_b=str(row["option_b"]).strip(),
                    option_c=str(row["option_c"]).strip(),
                    option_d=str(row["option_d"]).strip(),
                    correct_option=str(row["correct_answer"]).strip(),
                )
            else:
                payload = QuestionCreate(
                    **common,
                    question_format="fill_blank",
                    correct_answer_text=str(row["correct_answer"]).strip(),
                )
            valid.append(payload)
        except (ValidationError, ValueError) as e:
            errors.append(BulkImportRowError(row_number=i, errors=[str(e)], raw=row))

    return valid, errors
