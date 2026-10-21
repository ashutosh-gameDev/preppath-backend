"""course_note_pages table (admin-authored official notes per course/subject)

Revision ID: 0041_course_note_pages
Revises: 0040_subtopic_progress
Create Date: manual
"""
from alembic import op

revision = "0041_course_note_pages"
down_revision = "0040_subtopic_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE course_note_pages (
            id UUID NOT NULL,
            course_id UUID NOT NULL,
            subject_id UUID NOT NULL,
            title VARCHAR(255) NOT NULL DEFAULT 'Untitled',
            background VARCHAR(20) NOT NULL DEFAULT 'grid-dark',
            canvas_json TEXT NOT NULL DEFAULT '{}',
            order_index INTEGER NOT NULL DEFAULT 0,
            is_published BOOLEAN NOT NULL DEFAULT false,
            created_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id),
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
        )"""
    )
    op.execute("CREATE INDEX ix_course_note_pages_course_id ON course_note_pages (course_id)")
    op.execute("CREATE INDEX ix_course_note_pages_subject_id ON course_note_pages (subject_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS course_note_pages")
