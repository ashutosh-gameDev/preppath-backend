"""job_posting extra fields: job_type, stream, category, gender

Revision ID: 0028_job_posting_fields
Revises: 0027_mistake_dismissals
Create Date: manual

Adds four columns to job_postings so a posting can say what kind of job it
is (government/private), what broad sector it's in (banking, railways,
etc - a browse/filter tag, separate from the optional course_id link),
and two more eligibility-style filters (reservation category, gender) -
same "free text, null means no restriction" convention qualification
already uses, not a hard enum, so new values never need a migration.
Existing rows default to job_type='government', gender='all' (the most
common/least-restrictive values) so nothing already published looks wrong.
"""
from alembic import op

revision = "0028_job_posting_fields"
down_revision = "0027_mistake_dismissals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE job_postings ADD COLUMN job_type VARCHAR(20) NOT NULL DEFAULT 'government'")
    op.execute("ALTER TABLE job_postings ADD COLUMN stream VARCHAR(100)")
    op.execute("ALTER TABLE job_postings ADD COLUMN category VARCHAR(100)")
    op.execute("ALTER TABLE job_postings ADD COLUMN gender VARCHAR(10) NOT NULL DEFAULT 'all'")


def downgrade() -> None:
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS gender")
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS category")
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS stream")
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS job_type")
