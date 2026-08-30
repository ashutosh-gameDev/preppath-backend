"""
One-off generator for the initial Alembic migration.

Why this exists instead of `alembic revision --autogenerate`: autogenerate
needs a live Postgres connection to diff against, which isn't available in
every dev environment. This script instead compiles `Base.metadata` straight
to PostgreSQL DDL via SQLAlchemy's mock-engine mechanism (no connection
required) and writes it into a migration file with `op.execute`. The output
is byte-for-byte what `metadata.create_all()` would run against a real
Postgres database, so it's exactly as reliable as autogenerate for a
from-scratch initial migration. Re-run this only if you want to regenerate
0001 from scratch (e.g. before the first deploy) - normal schema changes
afterwards should use `alembic revision --autogenerate` against a real dev
database.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_mock_engine
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Base  # noqa

statements: list[str] = []


def _dump(sql, *multiparams, **params):
    statements.append(str(sql.compile(dialect=mock_engine.dialect)))


mock_engine = create_mock_engine("postgresql+psycopg://", _dump)
Base.metadata.create_all(mock_engine, checkfirst=False)

create_statements = [s.strip() for s in statements if s.strip()]

drop_statements = []
for table in reversed(Base.metadata.sorted_tables):
    drop_statements.append(f"DROP TABLE IF EXISTS {table.name} CASCADE;")

upgrade_body = "\n".join(f'    op.execute("""{s}""")' for s in create_statements)
downgrade_body = "\n".join(f'    op.execute("{s}")' for s in drop_statements)

migration = f'''"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: auto-generated

"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
{upgrade_body}


def downgrade() -> None:
{downgrade_body}
'''

out_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "0001_initial.py"
out_path.write_text(migration, encoding="utf-8")
print(f"Wrote {out_path} ({len(create_statements)} statements)")
