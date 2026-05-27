import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .core.config import settings
from .routers import auth, banner, board, goods_catalog, profile

app = FastAPI(title=settings.app_name)


def _static_dir() -> Path:
    # When packaged with PyInstaller (--onefile), bundled data lives under
    # sys._MEIPASS; otherwise it's next to this source file.
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "static"
    return Path(__file__).resolve().parent / "static"


_STATIC_DIR = _static_dir()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/admin")
def admin_console() -> FileResponse:
    """Admin web console (게시판 승인·배너·공지 관리). Any admin-credentialed
    user can log in; non-admins can open the page but every action 403s.
    Keep this path off your port-forward (access via http://localhost:PORT/admin
    on the server PC) if you want it LAN-only."""
    return FileResponse(_STATIC_DIR / "admin.html")


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(goods_catalog.router)
app.include_router(board.router)
app.include_router(banner.router)
