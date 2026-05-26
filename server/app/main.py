from fastapi import FastAPI

from .core.config import settings
from .routers import auth, goods_catalog, profile

app = FastAPI(title=settings.app_name)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(goods_catalog.router)
