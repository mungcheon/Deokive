"""Promote a user to admin (sets users.is_admin = True).

Admins can approve info-bot board posts, edit home banners, and moderate
any post via the API / admin console.

Usage:
    python make_admin.py <login_id>
    python make_admin.py --create <login_id> <password> <nickname>   # new admin

Run from the `server/` directory after the DB exists (init_sqlite_db.py).
"""
import sys

from app import models
from app.crud import create_local_user, get_user_by_login_id
from app.db import SessionLocal


def main(argv: list[str]) -> int:
    db = SessionLocal()
    try:
        if len(argv) >= 2 and argv[0] == "--create":
            login_id, password = argv[1], argv[2]
            nickname = argv[3] if len(argv) > 3 else login_id
            if get_user_by_login_id(db, login_id) is not None:
                print(f"User '{login_id}' already exists; promoting instead.")
            else:
                create_local_user(
                    db, login_id=login_id, password=password, nickname=nickname
                )
                print(f"Created user '{login_id}'.")
            target = login_id
        elif argv:
            target = argv[0]
        else:
            print(__doc__)
            return 1

        user = get_user_by_login_id(db, target)
        if user is None:
            print(f"User '{target}' not found. Sign up first or use --create.")
            return 1
        user.is_admin = True
        db.commit()
        print(f"OK: '{target}' is now an admin (user id {user.id}).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
