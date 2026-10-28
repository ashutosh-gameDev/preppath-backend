"""pyq_paper_negative_marking

Revision ID: c9f4a2e7b815
Revises: b7d2e9f1a3c6
Create Date: 2026-10-28 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c9f4a2e7b815'
down_revision: Union[str, None] = 'b7d2e9f1a3c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'pyq_papers',
        sa.Column('marks_per_question', sa.Float(), nullable=False, server_default=sa.text('1')),
    )
    op.add_column(
        'pyq_papers',
        sa.Column('negative_marking', sa.Float(), nullable=False, server_default=sa.text('0')),
    )


def downgrade() -> None:
    op.drop_column('pyq_papers', 'negative_marking')
    op.drop_column('pyq_papers', 'marks_per_question')
