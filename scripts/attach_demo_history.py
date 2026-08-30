"""
Copy one seeded demo student's attempt/XP/test history onto a real account so
the dashboard/analytics screens have something to show right after you sign
up locally.

Usage:
    python scripts/attach_demo_history.py --email you@example.com [--from "Aarav Sharma"]

Requires the target user row to already exist (see scripts/create_admin.py
docstring for why) and `python -m app.seed.seed_data` to have been run first.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.attempt import Attempt
from app.models.gamification import UserAchievement, XPTransaction
from app.models.test import TestAttempt
from app.models.user import Profile, User
from app.seed.seed_data import SEED_EMAIL_DOMAIN


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Your real (already-registered) account email")
    parser.add_argument("--from", dest="source_name", default="Aarav Sharma", help="Which seeded demo student to copy from")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        target = db.execute(select(User).where(User.email == args.email)).scalar_one_or_none()
        if target is None:
            print(f"No user found with email '{args.email}'. Sign up and load an authenticated page first.")
            sys.exit(1)

        source = db.execute(
            select(User).where(User.full_name == args.source_name, User.email.like(f"%{SEED_EMAIL_DOMAIN}"))
        ).scalar_one_or_none()
        if source is None:
            print(f"No seeded demo student named '{args.source_name}' found. Run `python -m app.seed.seed_data` first.")
            sys.exit(1)

        source_profile = db.get(Profile, source.id)
        target_profile = db.get(Profile, target.id)
        if target_profile is None:
            print(f"Target user '{args.email}' has no profile row yet - log in once via the app first.")
            sys.exit(1)

        db.query(Attempt).filter(Attempt.user_id == source.id).update({"user_id": target.id}, synchronize_session=False)
        db.query(TestAttempt).filter(TestAttempt.user_id == source.id).update({"user_id": target.id}, synchronize_session=False)
        db.query(XPTransaction).filter(XPTransaction.user_id == source.id).update({"user_id": target.id}, synchronize_session=False)
        db.query(UserAchievement).filter(UserAchievement.user_id == source.id).delete(synchronize_session=False)

        for field in [
            "xp_total", "level", "current_streak", "longest_streak", "last_activity_date",
            "questions_attempted", "questions_correct", "tests_completed", "pyqs_completed",
        ]:
            setattr(target_profile, field, getattr(source_profile, field))

        db.commit()
        print(f"Copied {args.source_name}'s history onto {args.email}. Refresh your dashboard.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
