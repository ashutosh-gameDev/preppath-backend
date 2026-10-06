"""ads + ad_events tables (CRM Ads Manager)

Revision ID: 0025_ads
Revises: 0024_pyq_paper_created_by
Create Date: manual

New tables only - nothing existing is touched. Backs the CRM's Ads Manager:
an admin creates/edits `ads` rows, each targeting a named `placement`
(matching a `slot="..."` in student-web's AdSlot); `ad_events` is a plain
impression/click log (not a counter) so CTR is always recomputed exactly.
"""
from alembic import op

revision = "0025_ads"
down_revision = "0024_pyq_paper_created_by"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE ads (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            title VARCHAR(255) NOT NULL,
            image_url VARCHAR(1000) NULL,
            link_url VARCHAR(1000) NULL,
            body_text TEXT NULL,
            placement VARCHAR(50) NOT NULL DEFAULT 'dashboard-mid',
            priority INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT true,
            starts_at TIMESTAMPTZ NULL,
            ends_at TIMESTAMPTZ NULL,
            created_by UUID NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
        )"""
    )
    op.execute("CREATE INDEX ix_ads_placement ON ads (placement)")
    op.execute("CREATE INDEX ix_ads_is_active ON ads (is_active)")

    op.execute(
        """CREATE TABLE ad_events (
            id UUID NOT NULL,
            ad_id UUID NOT NULL,
            event_type VARCHAR(10) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY(ad_id) REFERENCES ads (id) ON DELETE CASCADE
        )"""
    )
    op.execute("CREATE INDEX ix_ad_events_ad_id ON ad_events (ad_id)")
    op.execute("CREATE INDEX ix_ad_events_ad_id_event_type ON ad_events (ad_id, event_type)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ad_events")
    op.execute("DROP TABLE IF EXISTS ads")
