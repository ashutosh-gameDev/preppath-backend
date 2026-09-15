"""pyq_papers table + questions.pyq_paper_id, replacing questions.exam_id/year/source

Re-introduces the paper split from 0009 (reverted in 0010) - PYQ tagging
moves off `Exam` again, this time named unambiguously "PYQ Paper" everywhere
in the UI so it's never mistaken for the Notifications page's exams. See
app/models/pyq_paper.py.

Revision ID: 0012_pyq_papers
Revises: 0011_exam_event_courses
Create Date: manual

"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0012_pyq_papers"
down_revision = "0011_exam_event_courses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE pyq_papers (
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
    op.execute("CREATE INDEX ix_pyq_papers_exam_name ON pyq_papers (exam_name)")
    op.execute("CREATE INDEX ix_pyq_papers_course_id ON pyq_papers (course_id)")

    op.execute("ALTER TABLE questions ADD COLUMN pyq_paper_id UUID NULL REFERENCES pyq_papers (id) ON DELETE SET NULL")
    op.execute("CREATE INDEX ix_questions_pyq_paper_id ON questions (pyq_paper_id)")

    # Backfill: one PYQPaper per distinct (exam name, year, source) combo
    # among currently-tagged questions, grouped by NAME (not exam_id) so two
    # Exam rows sharing a name/year/source collapse into one paper instead
    # of tripping a duplicate. Every matching question is re-pointed at it
    # before the old columns go away.
    conn = op.get_bind()
    combos = conn.execute(
        sa.text(
            """
            SELECT DISTINCT e.name, q.year, q.source, q.language
            FROM questions q JOIN exams e ON e.id = q.exam_id
            WHERE q.exam_id IS NOT NULL
            """
        )
    ).fetchall()
    for exam_name, year, source, language in combos:
        paper_id = uuid.uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO pyq_papers (id, created_at, updated_at, exam_name, year, label, language)
                VALUES (:id, now(), now(), :exam_name, :year, :label, :language)
                """
            ),
            {"id": str(paper_id), "exam_name": exam_name, "year": year, "label": source, "language": language},
        )
        conn.execute(
            sa.text(
                """
                UPDATE questions q
                SET pyq_paper_id = :paper_id
                FROM exams e
                WHERE q.exam_id = e.id
                  AND e.name = :exam_name
                  AND q.year IS NOT DISTINCT FROM :year
                  AND q.source IS NOT DISTINCT FROM :label
                """
            ),
            {"paper_id": str(paper_id), "exam_name": exam_name, "year": year, "label": source},
        )

    op.execute("ALTER TABLE questions DROP COLUMN exam_id")
    op.execute("ALTER TABLE questions DROP COLUMN year")
    op.execute("ALTER TABLE questions DROP COLUMN source")


def downgrade() -> None:
    op.execute("ALTER TABLE questions ADD COLUMN exam_id UUID NULL REFERENCES exams (id) ON DELETE SET NULL")
    op.execute("ALTER TABLE questions ADD COLUMN year INTEGER NULL")
    op.execute("ALTER TABLE questions ADD COLUMN source VARCHAR(255) NULL")
    op.execute("CREATE INDEX ix_questions_exam_id ON questions (exam_id)")
    # Data is not restored (lossy the same way 0009's downgrade was).
    op.execute("DROP INDEX IF EXISTS ix_questions_pyq_paper_id")
    op.execute("ALTER TABLE questions DROP COLUMN pyq_paper_id")
    op.execute("DROP TABLE IF EXISTS pyq_papers CASCADE")
