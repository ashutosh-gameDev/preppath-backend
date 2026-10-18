"""profile gender/category (Jobs eligibility form completion)

Revision ID: 0036_profile_gender_category
Revises: 0035_ad_targeting_caps_format
Create Date: manual

Adds gender/category to Profile so the Jobs eligibility form (qualification,
city, state, gender, age, category) is fully persisted instead of gender/
category being session-only UI state - see jobs/page.tsx and users.py's
update_my_user. Both nullable; existing profiles are unaffected.
"""
from alembic import op

revision = "0036_profile_gender_category"
down_revision = "0035_ad_targeting_caps_format"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE profiles ADD COLUMN gender VARCHAR(10) NULL")
    op.execute("ALTER TABLE profiles ADD COLUMN category VARCHAR(20) NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS category")
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS gender")
