"""remove exam entirely

Revision ID: 0015_remove_exam
Revises: 0014_course_content_version
Create Date: manual

"""
from alembic import op

revision = "0015_remove_exam"
down_revision = "0014_course_content_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tests DROP COLUMN IF EXISTS exam_id")
    op.execute("DROP TABLE IF EXISTS exam_event_courses")
    op.execute("DROP TABLE IF EXISTS exam_events")
    op.execute("DROP TABLE IF EXISTS user_exam_follows")
    op.execute("DROP TABLE IF EXISTS exams")


def downgrade() -> None:
    op.execute(
        """CREATE TABLE exams (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            course_id UUID NULL, name VARCHAR(255) NOT NULL, slug VARCHAR(255) NOT NULL UNIQUE,
            description TEXT NULL, conducting_body VARCHAR(255) NULL, is_published BOOLEAN NOT NULL DEFAULT false,
            PRIMARY KEY (id), FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL
        )"""
    )
    op.execute(
        """CREATE TABLE exam_events (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            exam_id UUID NOT NULL, event_type VARCHAR(30) NOT NULL, title VARCHAR(255) NOT NULL,
            description TEXT NULL, event_date DATE NOT NULL, external_link VARCHAR(1000) NULL,
            is_published BOOLEAN NOT NULL DEFAULT true,
            PRIMARY KEY (id), FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE
        )"""
    )
    op.execute(
        """CREATE TABLE exam_event_courses (
            exam_event_id UUID NOT NULL, course_id UUID NOT NULL,
            PRIMARY KEY (exam_event_id, course_id),
            FOREIGN KEY(exam_event_id) REFERENCES exam_events (id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
        )"""
    )
    op.execute(
        """CREATE TABLE user_exam_follows (
            id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            user_id UUID NOT NULL, exam_id UUID NOT NULL, notifications_enabled BOOLEAN NOT NULL DEFAULT true,
            PRIMARY KEY (id), FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE,
            UNIQUE(user_id, exam_id)
        )"""
    )
    op.execute("ALTER TABLE tests ADD COLUMN exam_id UUID NULL REFERENCES exams(id) ON DELETE SET NULL")
