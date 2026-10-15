"""job_posting salary/fee/age_relaxation + profile city/state

Revision ID: 0029_job_salary_profile_geo
Revises: 0028_job_posting_fields
Create Date: manual

Adds three more free-text fields to job_postings (salary, application_fee,
age_relaxation) - government job ads typically state these as pay-scale/
category tables rather than single numbers (e.g. "Pay Level 4, Rs 25,500-
81,100" or "OBC: +3 yrs, SC/ST: +5 yrs"), so these stay descriptive text an
admin copies in, same convention as qualification/description. Also adds
city/state to profiles - personalization fields, not eligibility filters,
so nothing in jobs.py or notification_service.py needs to change.

Revision id kept <=32 chars - alembic_version.version_num is VARCHAR(32)
and a longer id fails that UPDATE, rolling back the whole migration
transaction (confirmed: 0029_job_salary_fee_relaxation_profile_location
failed this way and added no columns before being renamed to this).
"""
from alembic import op

revision = "0029_job_salary_profile_geo"
down_revision = "0028_job_posting_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE job_postings ADD COLUMN salary VARCHAR(255)")
    op.execute("ALTER TABLE job_postings ADD COLUMN application_fee TEXT")
    op.execute("ALTER TABLE job_postings ADD COLUMN age_relaxation TEXT")
    op.execute("ALTER TABLE profiles ADD COLUMN city VARCHAR(100)")
    op.execute("ALTER TABLE profiles ADD COLUMN state VARCHAR(100)")


def downgrade() -> None:
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS state")
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS city")
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS age_relaxation")
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS application_fee")
    op.execute("ALTER TABLE job_postings DROP COLUMN IF EXISTS salary")
