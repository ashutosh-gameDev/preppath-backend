"""payments: provider + google_play purchase columns (Android IAP)

Revision ID: 0042_google_play_payments
Revises: 0041_course_note_pages
Create Date: manual
"""
from alembic import op

revision = "0042_google_play_payments"
down_revision = "0041_course_note_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE payments ADD COLUMN provider VARCHAR(20) NOT NULL DEFAULT 'razorpay'")
    op.execute("ALTER TABLE payments ADD COLUMN google_play_product_id VARCHAR(64)")
    op.execute("ALTER TABLE payments ADD COLUMN google_play_purchase_token VARCHAR(500)")
    op.execute("CREATE INDEX ix_payments_google_play_purchase_token ON payments (google_play_purchase_token)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_payments_google_play_purchase_token")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS google_play_purchase_token")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS google_play_product_id")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS provider")
