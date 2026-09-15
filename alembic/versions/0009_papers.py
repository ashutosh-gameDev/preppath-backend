"""papers table + questions.paper_id, replacing questions.exam_id/year/source

Splits PYQ-paper tagging off the followable/notification `Exam` model (see
app/models/paper.py docstring) - a question's paper tag no longer requires
creating or picking an Exam row, so tagging a paper never clutters the exam
notifications list again. Existing (exam, year, source) combos on tagged
questions are preserved by creating one Paper per distinct combo and
re-pointing those questions at it before the old columns are dropped.

Revision ID: 0009_papers
Revises: 0008_question_subtopic
Create Date: manual

"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0009_papers"
down_revision = "0008_question_subtopic"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.execute("CREATE INDEX ix_papers_exam_name ON papers (exam_name)")
    op.execute("CREATE INDEX ix_papers_course_id ON papers (course_id)")

    op.execute("ALTER TABLE questions ADD COLUMN paper_id UUID NULL REFERENCES papers (id) ON DELETE SET NULL")
    op.execute("CREATE INDEX ix_questions_paper_id ON questions (paper_id)")

    # Backfill: one Paper per distinct (exam name, year, source) combo among
    # currently-tagged questions, grouped by NAME (not exam_id) so two Exam
    # rows that happen to share a name/year/source collapse into one Paper
    # instead of tripping a duplicate. Every matching question is then
    # re-pointed at it before the old columns go away.
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
                INSERT INTO papers (id, created_at, updated_at, exam_name, year, label, language)
                VALUES (:id, now(), now(), :exam_name, :year, :label, :language)
                """
            ),
            {"id": str(paper_id), "exam_name": exam_name, "year": year, "label": source, "language": language},
        )
        conn.execute(
            sa.text(
                """
                UPDATE questions q
                SET paper_id = :paper_id
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
    # Data is not restored on downgrade (exam_id/year/source -> paper_id was
    # lossy the moment exam identity collapsed to a free-text name) - this
    # only restores the schema shape, not the pre-migration values.
    op.execute("DROP INDEX IF EXISTS ix_questions_paper_id")
    op.execute("ALTER TABLE questions DROP COLUMN paper_id")
    op.execute("DROP TABLE IF EXISTS papers CASCADE")
