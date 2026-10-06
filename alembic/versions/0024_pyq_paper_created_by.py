"""pyq_papers.created_by (upload-ownership scoping)

Revision ID: 0024_pyq_paper_created_by
Revises: 0023_decks
Create Date: manual

Adds the same per-uploader ownership column `questions.created_by` already
has, so a team member only sees/edits the PYQ papers they created (see the
new _scope_own/_require_owned pair in admin/pyq_papers.py). Existing rows are
backfilled from their earliest tagged question's creator where known; papers
with no such question (or whose questions predate created_by tracking too)
are left NULL, which the new scoping treats as "only a super_admin sees it" -
the safe default for an ownerless legacy row.
"""
from alembic import op

revision = "0024_pyq_paper_created_by"
down_revision = "0023_decks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE pyq_papers ADD COLUMN created_by UUID NULL "
        "REFERENCES users (id) ON DELETE SET NULL"
    )
    op.execute("CREATE INDEX ix_pyq_papers_created_by ON pyq_papers (created_by)")
    op.execute(
        """
        UPDATE pyq_papers
        SET created_by = (
            SELECT q.created_by FROM questions q
            WHERE q.pyq_paper_id = pyq_papers.id AND q.created_by IS NOT NULL
            ORDER BY q.created_at ASC
            LIMIT 1
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE pyq_papers DROP COLUMN IF EXISTS created_by")
