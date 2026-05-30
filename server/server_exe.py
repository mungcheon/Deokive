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

from app.core.config import settings  # noqa: E402
from app.bootstrap import ensure_database_ready, ensure_sole_admin  # noqa: E402


def main() -> None:
    ensure_database_ready()
    created = ensure_sole_admin()
    print("=" * 52)
    if created:
        print(" [First run] Sole admin account created")
        print(f"   login_id : {created[0]}")
        print(f"   password : {created[1]}   (change this after login)")
        print("-" * 52)
    print(f" Sole admin account : {settings.sole_admin_login_id}")
    print(" Deokive server running -> http://0.0.0.0:8000")
    print("  - health : http://localhost:8000/health")
    print("  - admin  : http://localhost:8000/admin")
    print("  - board  : http://localhost:8000/board/posts")
    print("  External/app uses PUBLIC_IP:8000 (port-forward if needed)")
    print("  Stop: press Ctrl+C in this window")
    print("=" * 52)
    # Import string won't work in a frozen exe; pass the app object directly.
    from app.main import app

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
