"""
Promote an existing user to admin.

Usage:
    python scripts/create_admin.py --email you@example.com [--super]

The user row must already exist - it's lazily created the first time you
call any authenticated API endpoint after signing up via Supabase Auth in
the student (or admin) frontend. So the flow is:

    1. Sign up / log in once via the frontend (creates the Supabase auth
       user and, on the first authenticated API call, this backend's local
       `users` row).
    2. Run this script with that email to flip their role to admin/super_admin.
    3. Log in to the admin-web app with the same account.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--super", action="store_true", help="Grant super_admin instead of admin")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == args.email)).scalar_one_or_none()
        if user is None:
            print(
                f"No user found with email '{args.email}'. "
                "Sign up via the frontend and load any authenticated page first, then re-run this script."
            )
            sys.exit(1)
        user.role = UserRole.SUPER_ADMIN if args.super else UserRole.ADMIN
        db.commit()
        print(f"{args.email} is now {user.role}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
