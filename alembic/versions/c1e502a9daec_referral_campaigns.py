"""referral_campaigns

Revision ID: c1e502a9daec
Revises: ad44ad18aea6
Create Date: 2026-10-28 10:24:46.979048

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1e502a9daec'
down_revision: Union[str, None] = 'ad44ad18aea6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'referral_campaigns',
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('reward_days', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_referral_campaigns_code'), 'referral_campaigns', ['code'], unique=True)
    op.add_column('users', sa.Column('signup_campaign_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_users_signup_campaign_id'), 'users', ['signup_campaign_id'], unique=False)
    op.create_foreign_key(
        'fk_users_signup_campaign_id', 'users', 'referral_campaigns', ['signup_campaign_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_signup_campaign_id', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_signup_campaign_id'), table_name='users')
    op.drop_column('users', 'signup_campaign_id')
    op.drop_index(op.f('ix_referral_campaigns_code'), table_name='referral_campaigns')
    op.drop_table('referral_campaigns')
