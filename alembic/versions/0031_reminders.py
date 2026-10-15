"""reminders table

Revision ID: 0031_reminders
Revises: 0030_pyq_marks_time_limit
Create Date: manual

A student's own "remind me to study/sleep/whatever" entries - "daily"
(fires every day at time_of_day) or "once" (fires only on on_date). Purely
a schedule the student's own browser checks against the clock to show a
Notification while the app is open - there is no server-side push/cron
for this, so nothing here needs a "sent" flag or a delivery log.
"""
from alembic import op

revision = "0031_reminders"
down_revision = "0030_pyq_marks_time_limit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE reminders (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL,
            title VARCHAR(100) NOT NULL,
            kind VARCHAR(10) NOT NULL DEFAULT 'daily',
            time_of_day TIME NOT NULL,
            on_date DATE NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )"""
    )
    op.execute("CREATE INDEX ix_reminders_user_id ON reminders (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reminders")
