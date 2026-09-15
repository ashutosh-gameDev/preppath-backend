"""questions.subtopic_id (finer than topic_id - Topic="chapter", Subtopic="topic")

Revision ID: 0008_question_subtopic
Revises: 0007_subtopics
Create Date: manual

"""
from alembic import op

revision = "0008_question_subtopic"
down_revision = "0007_subtopics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE questions
        ADD COLUMN subtopic_id UUID NULL REFERENCES subtopics (id) ON DELETE SET NULL
        """
    )
    op.execute("CREATE INDEX ix_questions_subtopic_id ON questions (subtopic_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_questions_subtopic_id")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS subtopic_id")
