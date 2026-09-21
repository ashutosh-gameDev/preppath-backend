"""PYQ papers get a publish switch (students browse PYQ Question Papers directly)

Revision ID: 0019_pyq_paper_publish
Revises: 0018_protect_questions
Create Date: manual

Until now students only saw PYQ *tests* (Test rows with test_type='pyq') that
an admin built from a PYQ paper. Students now open the PYQ Question Paper
itself, so the paper needs its own published/draft flag - only a super admin
flips it. New and existing papers start as drafts, except the ones a student
could already see: a paper that has a published PYQ test with the same year and
label stays published so nothing disappears on deploy.
"""
import sqlalchemy as sa
from alembic import op

revision = "0019_pyq_paper_publish"
down_revision = "0018_protect_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pyq_papers",
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        """
        UPDATE pyq_papers p SET is_published = true
        WHERE EXISTS (
            SELECT 1 FROM tests t
            WHERE t.test_type = 'pyq' AND t.status = 'published'
              AND t.pyq_year IS NOT DISTINCT FROM p.year
              AND t.pyq_paper_label IS NOT DISTINCT FROM p.label
        )
        """
    )


def downgrade() -> None:
    op.drop_column("pyq_papers", "is_published")
