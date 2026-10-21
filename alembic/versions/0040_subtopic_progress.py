"""subtopic_progress table (per-student mark-complete/needs-revision tracking, one level below topic_progress)

Revision ID: 0040_subtopic_progress
Revises: 0039_video_watches
Create Date: manual
"""
from alembic import op

revision = "0040_subtopic_progress"
down_revision = "0039_video_watches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE subtopic_progress (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            subtopic_id UUID NOT NULL,
            is_completed BOOLEAN NOT NULL DEFAULT true,
            completed_at TIMESTAMPTZ,
            needs_revision BOOLEAN NOT NULL DEFAULT false,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(subtopic_id) REFERENCES subtopics (id) ON DELETE CASCADE,
            CONSTRAINT uq_subtopic_progress_user_subtopic UNIQUE (user_id, subtopic_id)
        )"""
    )
    op.execute("CREATE INDEX ix_subtopic_progress_user_id ON subtopic_progress (user_id)")
    op.execute("CREATE INDEX ix_subtopic_progress_subtopic_id ON subtopic_progress (subtopic_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subtopic_progress")
