"""course_enrollments gets an optional target exam date

Revision ID: 0022_enrollment_exam_date
Revises: 0021_question_bookmarks
Create Date: manual

Backs the student app's Home page exam-countdown card. Nullable, additive -
existing enrollment rows are unaffected and simply have no date until a
student sets one.
"""
from alembic import op

revision = "0022_enrollment_exam_date"
down_revision = "0021_question_bookmarks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE course_enrollments ADD COLUMN target_exam_date DATE NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE course_enrollments DROP COLUMN target_exam_date")
