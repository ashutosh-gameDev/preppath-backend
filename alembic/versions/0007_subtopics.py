"""subtopics table (topic -> subtopic -> multiple youtube videos)

Revision ID: 0007_subtopics
Revises: 0006_question_format_fill_blank
Create Date: manual

"""
from alembic import op

revision = "0007_subtopics"
down_revision = "0006_question_format_fill_blank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE subtopics (
            id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            topic_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0,
            is_published BOOLEAN NOT NULL DEFAULT false,
            youtube_videos VARCHAR[] NOT NULL DEFAULT '{}',
            PRIMARY KEY (id),
            FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE CASCADE,
            CONSTRAINT uq_subtopic_topic_slug UNIQUE (topic_id, slug)
        )
        """
    )
    op.execute("CREATE INDEX ix_subtopics_topic_id ON subtopics (topic_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subtopics CASCADE")
