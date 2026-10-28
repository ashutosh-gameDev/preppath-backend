"""question_bilingual_text

Revision ID: f3a1b7c2d4e5
Revises: c1e502a9daec
Create Date: 2026-10-28 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a1b7c2d4e5'
down_revision: Union[str, None] = 'c1e502a9daec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('questions', sa.Column('language_secondary', sa.String(length=50), nullable=True))
    op.add_column('questions', sa.Column('question_text_secondary', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('option_a_secondary', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('option_b_secondary', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('option_c_secondary', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('option_d_secondary', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('correct_answer_text_secondary', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('explanation_secondary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('questions', 'explanation_secondary')
    op.drop_column('questions', 'correct_answer_text_secondary')
    op.drop_column('questions', 'option_d_secondary')
    op.drop_column('questions', 'option_c_secondary')
    op.drop_column('questions', 'option_b_secondary')
    op.drop_column('questions', 'option_a_secondary')
    op.drop_column('questions', 'question_text_secondary')
    op.drop_column('questions', 'language_secondary')
