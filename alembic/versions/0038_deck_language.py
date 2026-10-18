"""Deck.language (Hindi/English content filtering)

Revision ID: 0038_deck_language
Revises: 0037_intern_payments
Create Date: manual

Lets a super admin tag a Study Bite deck as English/Hindi, same convention
as the existing PYQPaper.language - see decks.py's list_decks for the
student-facing "prefer Hindi, fall back to English" filter this backs.
"""
from alembic import op

revision = "0038_deck_language"
down_revision = "0037_intern_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE decks ADD COLUMN language VARCHAR(50) NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE decks DROP COLUMN IF EXISTS language")
