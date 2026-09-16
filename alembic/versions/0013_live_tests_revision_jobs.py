"""live PYQ tests (scheduled window), syllabus revision flag, job postings

Revision ID: 0013_live_tests_revision_jobs
Revises: 0012_pyq_papers
Create Date: manual

"""
from alembic import op

revision = "0013_live_tests_revision_jobs"
down_revision = "0012_pyq_papers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Live test scheduling - a Test (mock or PYQ) can optionally have a
    # start/end window; outside it, students can't start a new attempt (see
    # api/v1/endpoints/tests.py start_test). NULL start/end with is_live
    # false (the default) behaves exactly like today - untimed-window tests.
    op.execute("ALTER TABLE tests ADD COLUMN is_live BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE tests ADD COLUMN live_starts_at TIMESTAMP WITH TIME ZONE NULL")
    op.execute("ALTER TABLE tests ADD COLUMN live_ends_at TIMESTAMP WITH TIME ZONE NULL")

    # Syllabus: a topic can be marked "needs revision" independent of (and
    # possibly alongside) "completed" - e.g. finished once but want to
    # revisit before the exam.
    op.execute("ALTER TABLE topic_progress ADD COLUMN needs_revision BOOLEAN NOT NULL DEFAULT false")

    # Age/qualification used to filter the student-facing Jobs notification
    # tab to postings they're actually eligible for - optional, set once
    # from that tab (or the profile) and remembered.
    op.execute("ALTER TABLE profiles ADD COLUMN date_of_birth DATE NULL")
    op.execute("ALTER TABLE profiles ADD COLUMN qualification VARCHAR(100) NULL")

    op.execute(
        """
        CREATE TABLE job_postings (
            id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            title VARCHAR(255) NOT NULL,
            organization VARCHAR(255) NULL,
            description TEXT NULL,
            min_age INTEGER NULL,
            max_age INTEGER NULL,
            -- Free text (e.g. "10th Pass", "Graduate", "Any") rather than an
            -- enum, same extensibility reasoning as Question.language - a
            -- new qualification level never needs a migration.
            qualification VARCHAR(100) NULL,
            apply_link VARCHAR(1000) NULL,
            course_id UUID NULL,
            posted_date DATE NOT NULL,
            application_deadline DATE NULL,
            is_published BOOLEAN NOT NULL DEFAULT false,
            created_by UUID NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE SET NULL,
            FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_job_postings_is_published ON job_postings (is_published)")
    op.execute("CREATE INDEX ix_job_postings_posted_date ON job_postings (posted_date)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS job_postings CASCADE")
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS qualification")
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS date_of_birth")
    op.execute("ALTER TABLE topic_progress DROP COLUMN IF EXISTS needs_revision")
    op.execute("ALTER TABLE tests DROP COLUMN IF EXISTS live_ends_at")
    op.execute("ALTER TABLE tests DROP COLUMN IF EXISTS live_starts_at")
    op.execute("ALTER TABLE tests DROP COLUMN IF EXISTS is_live")
