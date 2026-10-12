"""FastAPI app.   Run (from backend/):   uvicorn app.main:app --reload"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, db
from .errors import install_error_handlers
from .routes import deliveries, ingestions, metrics


def create_app(db_path=None, frontend_dist=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = db.connect(app.state.db_path)
        db.init_db(conn)
        conn.close()
        yield

    app = FastAPI(title="Campaign Data Hub", version="1.0", lifespan=lifespan)
    app.state.db_path = db_path or config.DB_PATH
    origins = os.getenv("HUB_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
    install_error_handlers(app)
    for r in (metrics.router, deliveries.router, ingestions.router):
        app.include_router(r, prefix="/api/v1")

    # Mounted last so /api, /docs and /openapi.json keep priority over the static files.
    dist = Path(frontend_dist) if frontend_dist is not None else config.FRONTEND_DIST
    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    return app


app = create_app()
