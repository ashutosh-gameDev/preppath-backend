"""questions get a 'needs image' flag + note

Revision ID: 0020_question_needs_image
Revises: 0019_pyq_paper_publish
Create Date: manual

Bulk-imported questions (from a PDF/AI text extraction) sometimes reference a
diagram/figure/table that didn't come through as text. Nothing marked which
ones those were, so finding them again meant reading every question. This adds
a flag ('needs_image') and a short free-text note (what's missing) so the CRM
can filter straight to them; see api/v1/endpoints/admin/questions.py for the
auto-clear-on-image-add behavior.
"""
import sqlalchemy as sa
from alembic import op

revision = "0020_question_needs_image"
down_revision = "0019_pyq_paper_publish"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("needs_image", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("questions", sa.Column("image_note", sa.Text(), nullable=True))
    op.create_index("ix_questions_needs_image", "questions", ["needs_image"])


def downgrade() -> None:
    op.drop_index("ix_questions_needs_image", table_name="questions")
    op.drop_column("questions", "image_note")
    op.drop_column("questions", "needs_image")
