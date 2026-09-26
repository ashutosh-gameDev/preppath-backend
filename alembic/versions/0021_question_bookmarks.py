"""question bookmarks table

Revision ID: 0021_question_bookmarks
Revises: 0020_question_needs_image
Create Date: manual

New table only - nothing existing is touched. Backs the student app's
"Bookmarks" tool (save a question while practicing/browsing to revisit later).
"""
from alembic import op

revision = "0021_question_bookmarks"
down_revision = "0020_question_needs_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE question_bookmarks (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL, question_id UUID NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE,
            CONSTRAINT uq_question_bookmark UNIQUE (user_id, question_id)
        )"""
    )
    op.execute("CREATE INDEX ix_question_bookmarks_user_id ON question_bookmarks (user_id)")
    op.execute("CREATE INDEX ix_question_bookmarks_question_id ON question_bookmarks (question_id)")


def downgrade() -> None:
    op.execute("DROP TABLE question_bookmarks")
