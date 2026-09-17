"""normal/pro/premium user tiers

Revision ID: 0016_user_tiers
Revises: 0015_remove_exam
Create Date: manual

"""
from alembic import op

revision = "0016_user_tiers"
down_revision = "0015_remove_exam"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE profiles RENAME COLUMN premium_until TO tier_expires_at")
    op.execute("ALTER TABLE profiles ADD COLUMN tier VARCHAR(20) NOT NULL DEFAULT 'normal'")
    # Anyone with unexpired premium_until was, by definition, on the single
    # old "premium" tier - carry that forward instead of dropping them to
    # normal.
    op.execute("UPDATE profiles SET tier = 'premium' WHERE tier_expires_at IS NOT NULL AND tier_expires_at > now()")


def downgrade() -> None:
    op.execute("ALTER TABLE profiles DROP COLUMN tier")
    op.execute("ALTER TABLE profiles RENAME COLUMN tier_expires_at TO premium_until")
