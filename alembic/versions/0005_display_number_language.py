"""question display_number (human-friendly sequential id) + language tag

Revision ID: 0005_question_display_number_and_language
Revises: 0004_content_team_and_syllabus
Create Date: manual

"""
from alembic import op

revision = "0005_display_number_language"
down_revision = "0004_content_team_and_syllabus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE questions ADD COLUMN language VARCHAR(50)")

    # display_number: a short, stable, human-friendly number ("Q1042") for
    # admins/interns to reference a question without pasting a UUID.
    # Backfilled in creation order for existing rows, then handed to Postgres
    # as a normal sequence default so every future insert gets the next one
    # automatically - no application-side counter to keep in sync.
    op.execute("ALTER TABLE questions ADD COLUMN display_number INTEGER")
    op.execute(
        """
        UPDATE questions
        SET display_number = sub.rn
        FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS rn FROM questions) AS sub
        WHERE questions.id = sub.id
        """
    )
    op.execute(
        "CREATE SEQUENCE questions_display_number_seq OWNED BY questions.display_number"
    )
    op.execute(
        "SELECT setval('questions_display_number_seq', COALESCE((SELECT MAX(display_number) FROM questions), 0))"
    )
    op.execute("ALTER TABLE questions ALTER COLUMN display_number SET DEFAULT nextval('questions_display_number_seq')")
    op.execute("ALTER TABLE questions ALTER COLUMN display_number SET NOT NULL")
    op.execute("ALTER TABLE questions ADD CONSTRAINT uq_questions_display_number UNIQUE (display_number)")


def downgrade() -> None:
    op.execute("ALTER TABLE questions DROP CONSTRAINT IF EXISTS uq_questions_display_number")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS display_number")
    op.execute("DROP SEQUENCE IF EXISTS questions_display_number_seq")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS language")
