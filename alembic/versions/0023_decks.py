"""decks table (Study Bite)

Revision ID: 0023_decks
Revises: 0022_enrollment_exam_date
Create Date: manual

New table only - nothing existing is touched. Backs the admin CRM's
AI-generated "Study Bite" flashcard decks: an admin pastes AI-generated deck
JSON (validated by app.schemas.deck/deck_import_service), which is stored
here as one JSON blob (`cards`) alongside real course/subject/topic/subtopic
FKs for filtering, mirroring how `questions` is tagged.
"""
from alembic import op

revision = "0023_decks"
down_revision = "0022_enrollment_exam_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE decks (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            title VARCHAR(255) NOT NULL,
            description TEXT NULL,
            course_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            topic_id UUID NULL,
            subtopic_id UUID NULL,
            difficulty VARCHAR(10) NOT NULL DEFAULT 'medium',
            theme VARCHAR(50) NULL,
            estimated_minutes INTEGER NOT NULL DEFAULT 0,
            tags JSON NOT NULL,
            schema_version INTEGER NOT NULL DEFAULT 1,
            cards JSON NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            created_by UUID NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT,
            FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT,
            FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL,
            FOREIGN KEY(subtopic_id) REFERENCES subtopics (id) ON DELETE SET NULL,
            FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
        )"""
    )
    op.execute("CREATE INDEX ix_decks_course_id ON decks (course_id)")
    op.execute("CREATE INDEX ix_decks_subject_id ON decks (subject_id)")
    op.execute("CREATE INDEX ix_decks_status ON decks (status)")
    op.execute("CREATE INDEX ix_decks_created_by ON decks (created_by)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS decks")
