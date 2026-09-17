"""notes board (premium sync)

Revision ID: 0017_notes
Revises: 0016_user_tiers
Create Date: manual

"""
from alembic import op

revision = "0017_notes"
down_revision = "0016_user_tiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE note_categories (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL, name VARCHAR(100) NOT NULL, color VARCHAR(20) NOT NULL DEFAULT '#6366f1',
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )"""
    )
    op.execute("CREATE INDEX ix_note_categories_user_id ON note_categories (user_id)")

    op.execute(
        """CREATE TABLE note_pages (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL, category_id UUID NULL, title VARCHAR(255) NOT NULL DEFAULT 'Untitled',
            background VARCHAR(20) NOT NULL DEFAULT 'grid-dark', canvas_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES note_categories (id) ON DELETE SET NULL
        )"""
    )
    op.execute("CREATE INDEX ix_note_pages_user_id ON note_pages (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS note_pages")
    op.execute("DROP TABLE IF EXISTS note_categories")
