"""taxonomy_name_secondary

Revision ID: b7d2e9f1a3c6
Revises: f3a1b7c2d4e5
Create Date: 2026-10-28 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d2e9f1a3c6'
down_revision: Union[str, None] = 'f3a1b7c2d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('courses', sa.Column('name_secondary', sa.String(length=255), nullable=True))
    op.add_column('subjects', sa.Column('name_secondary', sa.String(length=255), nullable=True))
    op.add_column('topics', sa.Column('name_secondary', sa.String(length=255), nullable=True))
    op.add_column('subtopics', sa.Column('name_secondary', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('subtopics', 'name_secondary')
    op.drop_column('topics', 'name_secondary')
    op.drop_column('subjects', 'name_secondary')
    op.drop_column('courses', 'name_secondary')
