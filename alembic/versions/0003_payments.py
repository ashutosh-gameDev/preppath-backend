"""add payments table + profiles.premium_until

Revision ID: 0003_payments
Revises: 0002_course_enrollments
Create Date: manual

"""
from alembic import op

revision = "0003_payments"
down_revision = "0002_course_enrollments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE payments (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            plan VARCHAR(20) NOT NULL,
            amount_paise INTEGER NOT NULL,
            currency VARCHAR(3) DEFAULT 'INR' NOT NULL,
            razorpay_order_id VARCHAR(64),
            razorpay_payment_id VARCHAR(64),
            razorpay_signature VARCHAR(255),
            status VARCHAR(20) DEFAULT 'created' NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            paid_at TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX ix_payments_user_id ON payments (user_id)")
    op.execute("CREATE INDEX ix_payments_razorpay_order_id ON payments (razorpay_order_id)")
    op.execute("ALTER TABLE profiles ADD COLUMN premium_until TIMESTAMP WITH TIME ZONE")


def downgrade() -> None:
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS premium_until")
    op.execute("DROP TABLE IF EXISTS payments CASCADE;")
