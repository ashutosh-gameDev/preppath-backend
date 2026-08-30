"""Remove all seed/demo data (courses, questions, exams, tests, demo student
accounts) inserted by `python -m app.seed.seed_data`, leaving real user data
untouched. Safe to run any time - see seed_data.clear_seed_data for exactly
which rows are considered "seed data"."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.seed.seed_data import clear_seed_data


def main() -> None:
    db = SessionLocal()
    try:
        clear_seed_data(db)
        print("Seed data removed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
