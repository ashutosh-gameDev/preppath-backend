"""revert: drop papers table, restore questions.exam_id/year/source

The Paper/Exam split (0009) turned out to be more confusing than helpful in
practice - PYQ tagging goes back to directly referencing Exam (the same
entity used for notifications), exactly as it worked before 0009. Existing
paper_id tags are preserved: each distinct Paper becomes (or matches) a real
Exam row, and its questions are re-pointed at exam_id/year/source.

Revision ID: 0010_revert_papers
Revises: 0009_papers
Create Date: manual

"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0010_revert_papers"
down_revision = "0009_papers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE questions ADD COLUMN exam_id UUID NULL REFERENCES exams (id) ON DELETE SET NULL")
    op.execute("ALTER TABLE questions ADD COLUMN year INTEGER NULL")
    op.execute("ALTER TABLE questions ADD COLUMN source VARCHAR(255) NULL")

    conn = op.get_bind()
    papers = conn.execute(sa.text("SELECT id, exam_name, year, label FROM papers")).fetchall()
    for paper_id, exam_name, year, label in papers:
        exam_row = conn.execute(
            sa.text("SELECT id FROM exams WHERE lower(name) = lower(:name) LIMIT 1"), {"name": exam_name}
        ).fetchone()
        if exam_row:
            exam_id = exam_row[0]
        else:
            exam_id = uuid.uuid4()
            # Same slugify approach as _unique_slug in admin/exams.py, simplified
            # (good enough for a one-off migration backfill - collisions are
            # astronomically unlikely for real exam names).
            slug = exam_name.strip().lower().replace(" ", "-")
            conn.execute(
                sa.text(
                    """
                    INSERT INTO exams (id, created_at, updated_at, name, slug, is_published)
                    VALUES (:id, now(), now(), :name, :slug, false)
                    """
                ),
                {"id": str(exam_id), "name": exam_name, "slug": slug},
            )
        conn.execute(
            sa.text("UPDATE questions SET exam_id = :exam_id, year = :year, source = :label WHERE paper_id = :paper_id"),
            {"exam_id": str(exam_id), "year": year, "label": label, "paper_id": str(paper_id)},
        )

    op.execute("CREATE INDEX ix_questions_exam_id ON questions (exam_id)")
    op.execute("ALTER TABLE questions DROP COLUMN paper_id")
    op.execute("DROP TABLE IF EXISTS papers CASCADE")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE papers (
            id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            exam_name VARCHAR(255) NOT NULL,
            year INTEGER NULL,
            label VARCHAR(255) NULL,
            language VARCHAR(50) NULL,
            course_id UUID NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL
        )
        """
    )
    op.execute("ALTER TABLE questions ADD COLUMN paper_id UUID NULL REFERENCES papers (id) ON DELETE SET NULL")
    op.execute("CREATE INDEX ix_questions_paper_id ON questions (paper_id)")
    # Data is not restored (lossy the same way 0009's downgrade was).
    op.execute("DROP INDEX IF EXISTS ix_questions_exam_id")
    op.execute("ALTER TABLE questions DROP COLUMN exam_id")
    op.execute("ALTER TABLE questions DROP COLUMN year")
    op.execute("ALTER TABLE questions DROP COLUMN source")
