"""FastAPI application factory + lifespan (boots the infra substrate once).

`uvicorn api.main:app` serves the conversation API. The lifespan builds the AppState (config → LLM
clients → Postgres engine+init_db → Chroma store → orchestrator assembled from real-layer adapters)
and stores it at `app.state.nova`; the engine is disposed on shutdown.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.logging import RequestLoggingMiddleware
from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.state import build_app_state

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.nova = build_app_state()
    try:
        yield
    finally:
        engine = getattr(app.state.nova, "engine", None)
        if engine is not None and hasattr(engine, "dispose"):
            engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Nova AI", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware, allow_origins=["http://localhost:3000"],
        allow_methods=["*"], allow_headers=["*"])
    app.include_router(health_router)
    app.include_router(chat_router)
    return app


app = create_app()
