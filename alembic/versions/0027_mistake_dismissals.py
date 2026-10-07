"""mistake_dismissals table

Revision ID: 0027_mistake_dismissals
Revises: 0026_ad_courses
Create Date: manual

New table only. Lets a student manually clear a question off their
Mistake Book without re-answering it correctly - see models/
mistake_dismissal.py for why it's a separate table rather than a flag on
Attempt (the Mistake Book is otherwise fully derived, no flag of its own).
"""
from alembic import op

revision = "0027_mistake_dismissals"
down_revision = "0026_ad_courses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE mistake_dismissals (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            question_id UUID NOT NULL,
            dismissed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id),
            UNIQUE (user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
        )"""
    )
    op.execute("CREATE INDEX ix_mistake_dismissals_user_id ON mistake_dismissals (user_id)")
    op.execute("CREATE INDEX ix_mistake_dismissals_question_id ON mistake_dismissals (question_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mistake_dismissals")
