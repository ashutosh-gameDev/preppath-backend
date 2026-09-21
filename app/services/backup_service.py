"""
Content backup / restore. Exports everything an admin authored - the
course tree, PYQ papers, questions (with tags), tests, job postings - as one
JSON document, and can put missing rows back from such a document.

Generic on purpose (driven by each table's own columns) so a newly added
column is picked up automatically instead of silently missing from backups.
Restore is additive and idempotent: it only inserts rows whose primary key is
absent, never overwrites or deletes anything.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.models.course import Course, Subject, Subtopic, Topic
from app.models.job_posting import JobPosting
from app.models.pyq_paper import PYQPaper
from app.models.question import Question, Tag, question_tags
from app.models.test import Test, TestQuestion, TestSection

# Parents before children so restore never violates a foreign key.
MODELS = [Course, Subject, Topic, Subtopic, PYQPaper, Tag, Question, Test, TestSection, TestQuestion, JobPosting]


def _to_json(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _from_json(column, value):
    if value is None:
        return None
    py = column.type.python_type
    if py is uuid.UUID:
        return uuid.UUID(value)
    if py is datetime:
        return datetime.fromisoformat(value)
    if py is date:
        return date.fromisoformat(value)
    return value


def export_content(db: Session) -> dict:
    data: dict = {}
    for model in MODELS:
        cols = [c.key for c in model.__table__.columns]
        rows = db.execute(select(model)).scalars().all()
        data[model.__tablename__] = [{k: _to_json(getattr(r, k)) for k in cols} for r in rows]
    data["question_tags"] = [
        {"question_id": str(q), "tag_id": str(t)}
        for q, t in db.execute(select(question_tags.c.question_id, question_tags.c.tag_id)).all()
    ]
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "counts": {name: len(rows) for name, rows in data.items()},
        "tables": data,
    }


def restore_content(db: Session, backup: dict, dry_run: bool = False) -> dict[str, int]:
    """Inserts every row from `backup` whose primary key isn't already in the
    database. Returns {table: rows_inserted}."""
    tables = backup["tables"]
    inserted: dict[str, int] = {}
    for model in MODELS:
        pk = list(model.__table__.primary_key.columns.keys())[0]
        existing = {str(v) for v in db.execute(select(getattr(model, pk))).scalars().all()}
        count = 0
        for row in tables.get(model.__tablename__, []):
            if str(row[pk]) in existing:
                continue
            values = {c.key: _from_json(c, row.get(c.key)) for c in model.__table__.columns if c.key in row}
            if not dry_run:
                db.execute(insert(model.__table__).values(**values))
            count += 1
        inserted[model.__tablename__] = count
        if not dry_run:
            db.flush()

    have = {(str(q), str(t)) for q, t in db.execute(select(question_tags.c.question_id, question_tags.c.tag_id)).all()}
    links = 0
    for row in tables.get("question_tags", []):
        if (row["question_id"], row["tag_id"]) in have:
            continue
        if not dry_run:
            db.execute(
                insert(question_tags).values(question_id=uuid.UUID(row["question_id"]), tag_id=uuid.UUID(row["tag_id"]))
            )
        links += 1
    inserted["question_tags"] = links
    return inserted
