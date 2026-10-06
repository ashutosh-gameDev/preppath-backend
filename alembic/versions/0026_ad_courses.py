"""ad_courses join table (course targeting for ads)

Revision ID: 0026_ad_courses
Revises: 0025_ads
Create Date: manual

New table only. Lets an ad target one or more specific courses; no rows
for an ad means untargeted (shown regardless of course).
"""
from alembic import op

revision = "0026_ad_courses"
down_revision = "0025_ads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE ad_courses (
            ad_id UUID NOT NULL,
            course_id UUID NOT NULL,
            PRIMARY KEY (ad_id, course_id),
            FOREIGN KEY(ad_id) REFERENCES ads (id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
        )"""
    )
    op.execute("CREATE INDEX ix_ad_courses_course_id ON ad_courses (course_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ad_courses")
