"""pyq_paper max_marks + time_limit_minutes

Revision ID: 0030_pyq_marks_time_limit
Revises: 0029_job_salary_profile_geo
Create Date: manual

Both nullable, no default - an admin fills these in per paper (from the
CRM form) rather than every paper getting a guessed value. A null
time_limit_minutes means the attempt page shows no countdown and never
auto-submits, same "null means not set" convention used elsewhere in this
codebase (e.g. JobPosting.qualification).
"""
from alembic import op

revision = "0030_pyq_marks_time_limit"
down_revision = "0029_job_salary_profile_geo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE pyq_papers ADD COLUMN max_marks FLOAT")
    op.execute("ALTER TABLE pyq_papers ADD COLUMN time_limit_minutes INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE pyq_papers DROP COLUMN IF EXISTS time_limit_minutes")
    op.execute("ALTER TABLE pyq_papers DROP COLUMN IF EXISTS max_marks")
