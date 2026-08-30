"""content editor accounts, per-option images, syllabus videos + progress

Revision ID: 0004_content_team_and_syllabus
Revises: 0003_payments
Create Date: manual

"""
from alembic import op

revision = "0004_content_team_and_syllabus"
down_revision = "0003_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN username VARCHAR(100)")
    op.execute("CREATE UNIQUE INDEX ix_users_username ON users (username) WHERE username IS NOT NULL")

    op.execute("ALTER TABLE questions ADD COLUMN option_a_image VARCHAR(1000)")
    op.execute("ALTER TABLE questions ADD COLUMN option_b_image VARCHAR(1000)")
    op.execute("ALTER TABLE questions ADD COLUMN option_c_image VARCHAR(1000)")
    op.execute("ALTER TABLE questions ADD COLUMN option_d_image VARCHAR(1000)")

    op.execute("ALTER TABLE topics ADD COLUMN video_url VARCHAR(1000)")

    op.execute(
        """
        CREATE TABLE topic_progress (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            topic_id UUID NOT NULL,
            is_completed BOOLEAN DEFAULT true NOT NULL,
            completed_at TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE CASCADE,
            CONSTRAINT uq_topic_progress_user_topic UNIQUE (user_id, topic_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_topic_progress_user_id ON topic_progress (user_id)")
    op.execute("CREATE INDEX ix_topic_progress_topic_id ON topic_progress (topic_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS topic_progress CASCADE;")
    op.execute("ALTER TABLE topics DROP COLUMN IF EXISTS video_url")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS option_a_image")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS option_b_image")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS option_c_image")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS option_d_image")
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS username")
