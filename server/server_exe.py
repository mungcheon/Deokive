"""Standalone entry point for the packaged Deokive server (.exe).

Double-clicking the built executable runs this: it ensures the SQLite tables
exist, prints the access URLs, then serves the FastAPI app with uvicorn.
The DB file (deokive_dev.db) is created next to the .exe so data persists
across runs.
"""
import os
import sys

# Keep the DB next to the executable (not the temp extract dir) so posts
# persist between launches.
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

import uvicorn  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app import models  # noqa: F401,E402  (register tables on metadata)
from app.crud import create_local_user, get_user_by_login_id  # noqa: E402


def _ensure_admin() -> tuple[str, str] | None:
    """Create a default admin on first run if none exists. Credentials come
    from env (DEOKIVE_ADMIN_ID / DEOKIVE_ADMIN_PW) or fall back to defaults,
    and are printed so the operator can log in to /admin immediately."""
    db = SessionLocal()
    try:
        has_admin = (
            db.query(models.User).filter(models.User.is_admin.is_(True)).first()
            is not None
        )
        if has_admin:
            return None
        admin_id = os.environ.get("DEOKIVE_ADMIN_ID", "admin")
        admin_pw = os.environ.get("DEOKIVE_ADMIN_PW", "deokiveadmin")
        user = get_user_by_login_id(db, admin_id)
        if user is None:
            user = create_local_user(
                db, login_id=admin_id, password=admin_pw, nickname="관리자"
            )
        user.is_admin = True
        db.commit()
        return admin_id, admin_pw
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    created = _ensure_admin()
    print("=" * 52)
    if created:
        print(f" [최초 실행] 관리자 계정 생성됨")
        print(f"   아이디 : {created[0]}")
        print(f"   비번   : {created[1]}   (보안 위해 변경 권장)")
        print("-" * 52)
    print(" Deokive 서버 실행 중  ->  http://0.0.0.0:8000")
    print("  - 상태   : http://localhost:8000/health")
    print("  - 관리자 : http://localhost:8000/admin")
    print("  - 게시판 : http://localhost:8000/board/posts")
    print("  외부/앱 : 공인IP:8000  (포트포워드 필요)")
    print("  멈추기  : 이 창에서 Ctrl+C  또는 창 닫기")
    print("=" * 52)
    # Import string won't work in a frozen exe; pass the app object directly.
    from app.main import app

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
