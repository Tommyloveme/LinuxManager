from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal, init_db
from app.modules.auth.service import AuthService
from app.modules.bootstrap import seed_if_empty

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    settings.ensure_dirs()
    await init_db()
    async with SessionLocal() as db:
        await AuthService(db).ensure_admin(settings.admin_username, settings.admin_password)
        await seed_if_empty(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api/health")
    async def health() -> dict:
        return {"ok": True, "name": settings.app_name, "version": settings.app_version}

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="ui")
    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
