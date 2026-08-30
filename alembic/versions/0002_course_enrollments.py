"""add course_enrollments table

Revision ID: 0002_course_enrollments
Revises: 0001_initial
Create Date: manual

"""
from alembic import op

revision = "0002_course_enrollments"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE course_enrollments (
            id UUID NOT NULL,
            user_id UUID NOT NULL,
            course_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            CONSTRAINT uq_course_enrollment UNIQUE (user_id, course_id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX ix_course_enrollments_user_id ON course_enrollments (user_id)")
    op.execute("CREATE INDEX ix_course_enrollments_course_id ON course_enrollments (course_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS course_enrollments CASCADE;")
