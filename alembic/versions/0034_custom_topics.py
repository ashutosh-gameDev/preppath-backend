"""custom_topics table (student's own syllabus checklist items)

Revision ID: 0034_custom_topics
Revises: 0033_referral_leaderboard
Create Date: manual

A student's own checklist items added under a subject, separate from the
admin-authored topics table - see models/custom_topic.py.
"""
from alembic import op

revision = "0034_custom_topics"
down_revision = "0033_referral_leaderboard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE custom_topics (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            is_completed BOOLEAN NOT NULL DEFAULT false,
            order_index INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE
        )"""
    )
    op.execute("CREATE INDEX ix_custom_topics_user_id ON custom_topics (user_id)")
    op.execute("CREATE INDEX ix_custom_topics_subject_id ON custom_topics (subject_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS custom_topics")
