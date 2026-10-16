"""referral code/attribution + study_sessions + leaderboard_rewards

Revision ID: 0033_referral_leaderboard
Revises: 0032_qualification_text
Create Date: manual

Three additions for two new growth features:
1. Referral program: every user gets a unique referral_code (backfilled
   for existing rows via Postgres's own random()/md5(), then made
   NOT NULL + unique); referred_by records who brought in a NEW signup.
   Reward (Pro days) is granted by POST /referrals/claim, not here.
2. study_sessions: one row per completed Study Timer session
   (user_id, duration_seconds) - append-only ledger, same convention as
   attempts/xp_transactions.
3. leaderboard_rewards: records which (period, rank_position) pairs have
   already been rewarded, so the monthly top-10-by-study-hours payout
   (computed lazily whenever anyone loads the leaderboard after month
   end, see study_leaderboard_service.py) never double-grants.
"""
from alembic import op

revision = "0033_referral_leaderboard"
down_revision = "0032_qualification_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN referral_code VARCHAR(12)")
    op.execute("ALTER TABLE users ADD COLUMN referred_by UUID REFERENCES users (id) ON DELETE SET NULL")
    op.execute(
        "UPDATE users SET referral_code = upper(substr(md5(random()::text || id::text), 1, 8)) "
        "WHERE referral_code IS NULL"
    )
    op.execute("ALTER TABLE users ALTER COLUMN referral_code SET NOT NULL")
    op.execute("CREATE UNIQUE INDEX ux_users_referral_code ON users (referral_code)")
    op.execute("CREATE INDEX ix_users_referred_by ON users (referred_by)")

    op.execute(
        """CREATE TABLE study_sessions (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL,
            duration_seconds INTEGER NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )"""
    )
    op.execute("CREATE INDEX ix_study_sessions_user_id ON study_sessions (user_id)")
    op.execute("CREATE INDEX ix_study_sessions_created_at ON study_sessions (created_at)")

    op.execute(
        """CREATE TABLE leaderboard_rewards (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            period VARCHAR(7) NOT NULL,
            rank_position INTEGER NOT NULL,
            user_id UUID NOT NULL,
            total_seconds INTEGER NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE (period, rank_position)
        )"""
    )
    op.execute("CREATE INDEX ix_leaderboard_rewards_period ON leaderboard_rewards (period)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS leaderboard_rewards")
    op.execute("DROP TABLE IF EXISTS study_sessions")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS referred_by")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS referral_code")
