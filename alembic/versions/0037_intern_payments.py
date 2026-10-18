"""intern_payments table + PYQPaper.payment_amount_paise

Revision ID: 0037_intern_payments
Revises: 0036_profile_gender_category
Create Date: manual

Lets a super admin price a PYQ paper (per-paper override, null = platform
default rate) and record payouts to an intern against the papers they've
uploaded - see models/intern_payment.py and intern_payment_service.py.
"""
from alembic import op

revision = "0037_intern_payments"
down_revision = "0036_profile_gender_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE pyq_papers ADD COLUMN payment_amount_paise INTEGER NULL")
    op.execute(
        """CREATE TABLE intern_payments (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            amount_paise INTEGER NOT NULL,
            note VARCHAR(255),
            paid_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
        )"""
    )
    op.execute("CREATE INDEX ix_intern_payments_user_id ON intern_payments (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS intern_payments")
    op.execute("ALTER TABLE pyq_papers DROP COLUMN IF EXISTS payment_amount_paise")
