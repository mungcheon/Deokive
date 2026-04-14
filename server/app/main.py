from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .crud import ensure_bootstrap_admin
from .db import SessionLocal
from .routers import (
    admin_auth,
    admin_backups,
    admin_catalog,
    admin_dashboard,
    admin_support,
    admin_users,
    auth,
    backup,
    profile,
)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4174",
        "http://localhost:4174",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_bootstrap_admin() -> None:
    db = SessionLocal()
    try:
        ensure_bootstrap_admin(
            db,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            display_name=settings.bootstrap_admin_name,
        )
    finally:
        db.close()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(backup.router)
app.include_router(admin_auth.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_users.router)
app.include_router(admin_backups.router)
app.include_router(admin_support.router)
app.include_router(admin_catalog.router)
