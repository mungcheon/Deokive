"""Create or promote the configured sole admin account.

This script no longer grants admin rights to arbitrary users. It only ensures
the login id configured in `.env` is the single admin account.

Usage:
    python make_admin.py
    python make_admin.py --create <password> [nickname]
"""
import sys

from app import models
from app.core.config import settings
from app.crud import create_local_user, get_user_by_login_id
from app.db import SessionLocal


def main(argv: list[str]) -> int:
    db = SessionLocal()
    try:
        login_id = settings.sole_admin_login_id
        password = settings.sole_admin_password
        nickname = settings.sole_admin_nickname

        if len(argv) >= 2 and argv[0] == "--create":
            password = argv[1]
            if len(argv) >= 3:
                nickname = argv[2]
        elif argv:
            print("This command only manages the configured sole admin account.")
            print(f"Configured login_id: {login_id}")
            return 1

        user = get_user_by_login_id(db, login_id)
        if user is None:
            create_local_user(
                db,
                login_id=login_id,
                password=password,
                nickname=nickname,
            )
            print(f"Created sole admin user '{login_id}'.")

        for other in db.query(models.User).all():
            other.is_admin = other.login_id == login_id
        db.commit()
        print(f"OK: '{login_id}' is now the only admin account.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
