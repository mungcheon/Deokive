from fastapi import FastAPI

from .core.config import settings
from .routers import auth, profile

app = FastAPI(title=settings.app_name)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(profile.router)
