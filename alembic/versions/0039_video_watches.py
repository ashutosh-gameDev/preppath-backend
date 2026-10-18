"""video_watches table (per-student "mark video watched" tracking)

Revision ID: 0039_video_watches
Revises: 0038_deck_language
Create Date: manual

Backs the Dashboard's new Videos card - see models/video_watch.py. Videos
have no table of their own (they're Topic.video_url / Subtopic.youtube_videos
URLs), so this keys on (user_id, video_url) rather than a video FK.
"""
from alembic import op

revision = "0039_video_watches"
down_revision = "0038_deck_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE video_watches (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            video_url VARCHAR(1000) NOT NULL,
            watched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            CONSTRAINT uq_video_watches_user_url UNIQUE (user_id, video_url)
        )"""
    )
    op.execute("CREATE INDEX ix_video_watches_user_id ON video_watches (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS video_watches")
