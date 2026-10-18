"""ad targeting (states/cities), auto-pause caps, and fullscreen format

Revision ID: 0035_ad_targeting_caps_format
Revises: 0034_custom_topics
Create Date: manual

Adds state/city targeting to Ad (same empty=untargeted convention as
ad_courses), max_impressions/max_clicks auto-pause caps, and the
format/interstitial_every_n columns backing the new Study Bite fullscreen
ad format. All new columns are additive and defaulted so every existing Ad
row keeps serving exactly as before (format='banner', states=[], cities=[],
caps unset, cadence unset) - see models/ad.py.
"""
from alembic import op

revision = "0035_ad_targeting_caps_format"
down_revision = "0034_custom_topics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ads ADD COLUMN states JSON NOT NULL DEFAULT '[]'::json")
    op.execute("ALTER TABLE ads ADD COLUMN cities JSON NOT NULL DEFAULT '[]'::json")
    op.execute("ALTER TABLE ads ADD COLUMN format VARCHAR(20) NOT NULL DEFAULT 'banner'")
    op.execute("ALTER TABLE ads ADD COLUMN max_impressions INTEGER NULL")
    op.execute("ALTER TABLE ads ADD COLUMN max_clicks INTEGER NULL")
    op.execute("ALTER TABLE ads ADD COLUMN interstitial_every_n INTEGER NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS interstitial_every_n")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS max_clicks")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS max_impressions")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS format")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS cities")
    op.execute("ALTER TABLE ads DROP COLUMN IF EXISTS states")
