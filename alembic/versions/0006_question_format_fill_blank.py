"""question_format (mcq/fill_blank) + correct_answer_text

Revision ID: 0006_question_format_fill_blank
Revises: 0005_display_number_language
Create Date: manual

"""
from alembic import op

revision = "0006_question_format_fill_blank"
down_revision = "0005_display_number_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE questions ADD COLUMN question_format VARCHAR(20) NOT NULL DEFAULT 'mcq'")
    op.execute("CREATE INDEX ix_questions_question_format ON questions (question_format)")
    op.execute("ALTER TABLE questions ADD COLUMN correct_answer_text TEXT")

    # Every existing row is an MCQ with all 4 options + correct_option already
    # set, so loosening these to nullable is safe - nothing currently in the
    # table would violate ck_questions_format_fields below.
    op.execute("ALTER TABLE questions ALTER COLUMN option_a DROP NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN option_b DROP NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN option_c DROP NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN option_d DROP NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN correct_option DROP NOT NULL")

    op.execute(
        """
        ALTER TABLE questions ADD CONSTRAINT ck_questions_format_fields CHECK (
            (question_format = 'mcq' AND option_a IS NOT NULL AND option_b IS NOT NULL
                AND option_c IS NOT NULL AND option_d IS NOT NULL AND correct_option IS NOT NULL)
            OR
            (question_format = 'fill_blank' AND correct_answer_text IS NOT NULL)
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE questions DROP CONSTRAINT IF EXISTS ck_questions_format_fields")
    # Refuses to downgrade past any fill_blank rows already created - they'd
    # have NULL options, which would violate the NOT NULL being restored.
    op.execute("DELETE FROM questions WHERE question_format = 'fill_blank'")
    op.execute("ALTER TABLE questions ALTER COLUMN option_a SET NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN option_b SET NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN option_c SET NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN option_d SET NOT NULL")
    op.execute("ALTER TABLE questions ALTER COLUMN correct_option SET NOT NULL")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS correct_answer_text")
    op.execute("DROP INDEX IF EXISTS ix_questions_question_format")
    op.execute("ALTER TABLE questions DROP COLUMN IF EXISTS question_format")
