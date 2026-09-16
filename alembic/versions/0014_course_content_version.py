"""course content_version

Revision ID: 0014_course_content_version
Revises: 0013_live_tests_revision_jobs
Create Date: manual

"""
from alembic import op

revision = "0014_course_content_version"
down_revision = "0013_live_tests_revision_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE courses ADD COLUMN content_version INTEGER NOT NULL DEFAULT 1")


def downgrade() -> None:
    op.execute("ALTER TABLE courses DROP COLUMN content_version")
