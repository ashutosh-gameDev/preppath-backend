"""stop course/subject deletes from silently deleting their questions

Revision ID: 0018_protect_questions
Revises: 0017_notes
Create Date: manual

questions.course_id / subject_id were ON DELETE CASCADE, so deleting a course
(or subject) in the CRM quietly wiped every question inside it - while the
admin delete endpoints and the confirmation dialog both claimed such a delete
would be refused. RESTRICT makes the database refuse it, which is what those
endpoints were written to expect.
"""
from alembic import op

revision = "0018_protect_questions"
down_revision = "0017_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE questions DROP CONSTRAINT questions_course_id_fkey")
    op.execute(
        "ALTER TABLE questions ADD CONSTRAINT questions_course_id_fkey "
        "FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE RESTRICT"
    )
    op.execute("ALTER TABLE questions DROP CONSTRAINT questions_subject_id_fkey")
    op.execute(
        "ALTER TABLE questions ADD CONSTRAINT questions_subject_id_fkey "
        "FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE RESTRICT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE questions DROP CONSTRAINT questions_course_id_fkey")
    op.execute(
        "ALTER TABLE questions ADD CONSTRAINT questions_course_id_fkey "
        "FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE questions DROP CONSTRAINT questions_subject_id_fkey")
    op.execute(
        "ALTER TABLE questions ADD CONSTRAINT questions_subject_id_fkey "
        "FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE"
    )
