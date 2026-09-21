"""
Put content back from a backup JSON downloaded from the CRM (Settings ->
Download backup). Additive only: inserts rows whose id is missing, never
overwrites or deletes.

    python scripts/restore_content.py backup.json --dry-run   # see what would be restored
    python scripts/restore_content.py backup.json             # restore
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.services.backup_service import restore_content  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    dry = "--dry-run" in sys.argv
    backup = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        result = restore_content(db, backup, dry_run=dry)
        if dry:
            db.rollback()
        else:
            db.commit()
        print(("DRY RUN - would insert: " if dry else "Inserted: ") + json.dumps(result))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
