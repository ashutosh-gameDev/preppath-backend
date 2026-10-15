"""widen job_postings.qualification to TEXT

Revision ID: 0032_qualification_text
Revises: 0031_reminders
Create Date: manual

qualification was VARCHAR(100), sized for the admin form's short dropdown
values ("12th Pass", "Graduate", ...). The JSON-import flow (an admin
pastes an LLM's JSON reply) routinely produces a full descriptive
sentence instead (e.g. "12th (10+2) or equivalent from a recognized
board. Typing proficiency is required for applicable clerical posts." -
112 chars), which Postgres rejected outright with StringDataRightTruncation.
That crashed the request with an unhandled 500 that carried no CORS
headers (FastAPI's default error path sits outside CORSMiddleware), which
the browser then misreported as a CORS policy block. Widening to
unbounded TEXT - same convention already used for description/
application_fee/age_relaxation - fixes the crash outright.
"""
from alembic import op

revision = "0032_qualification_text"
down_revision = "0031_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE job_postings ALTER COLUMN qualification TYPE TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE job_postings ALTER COLUMN qualification TYPE VARCHAR(100)")
