"""exam_event_courses (course-scoped notification delivery, replacing follow-only)

Notifications move from "student follows this exam" to "student is enrolled
in a course this notification targets" (or the notification targets no
course at all, meaning everyone) - see models/exam.py's ExamEvent docstring
and services/notification_service.py.

Revision ID: 0011_exam_event_courses
Revises: 0010_revert_papers
Create Date: manual

"""
from alembic import op

revision = "0011_exam_event_courses"
down_revision = "0010_revert_papers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE exam_event_courses (
            exam_event_id UUID NOT NULL,
            course_id UUID NOT NULL,
            PRIMARY KEY (exam_event_id, course_id),
            FOREIGN KEY(exam_event_id) REFERENCES exam_events (id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX ix_exam_event_courses_course_id ON exam_event_courses (course_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS exam_event_courses CASCADE")
