import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .bootstrap import ensure_database_ready, ensure_sole_admin
from .core.config import settings
from .routers import auth, banner, board, goods_catalog, profile


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_database_ready()
    ensure_sole_admin()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


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
    """Admin web console.

    The page is public to open, but only the configured sole-admin account can
    perform admin actions after login.
    """
    return FileResponse(_STATIC_DIR / "admin.html")


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(goods_catalog.router)
app.include_router(board.router)
app.include_router(banner.router)
