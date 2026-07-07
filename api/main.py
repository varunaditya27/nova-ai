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

from config import load_config
from api.middleware.logging import RequestLoggingMiddleware
from api.routes.chat import router as chat_router
from api.routes.goals import router as goals_router
from api.routes.health import router as health_router
from api.routes.memory import router as memory_router
from api.routes.onboarding import router as onboarding_router
from api.routes.safety import router as safety_router
from api.routes.sessions import router as sessions_router
from api.routes.tools import router as tools_router
from api.routes.sync import router as sync_router
from api.routes.proactive import router as proactive_router
from api.routes.longitudinal import router as longitudinal_router
from api.routes.admin import router as admin_router
from api.routes.relationship import router as relationship_router
from api.routes.voice import router as voice_router
from api.routes.messages import router as messages_router
from api.routes.continuity import router as continuity_router
from api.state import build_app_state

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.nova = build_app_state()
    scheduler = None
    try:
        from background.scheduler import start_scheduler
        scheduler = start_scheduler(app.state.nova)   # no-op unless config.scheduler.enabled
    except Exception:
        logging.getLogger("nova.api").exception("scheduler failed to start; continuing without it")
    try:
        yield
    finally:
        if scheduler is not None and hasattr(scheduler, "shutdown"):
            scheduler.shutdown(wait=False)
        engine = getattr(app.state.nova, "engine", None)
        if engine is not None and hasattr(engine, "dispose"):
            engine.dispose()


def _cors_origins() -> list[str]:
    """Read allowed origins from config (defaults.yaml + optional local.yaml overlay) so the
    frontend dev can point any origin (Vite :5173, a deployed host, …) at the API without a code
    change. Falls back to the localhost dev origin if config is unreadable."""
    try:
        cfg = load_config("local.yaml")
    except Exception:
        cfg = {}
    origins = (cfg.get("api") or {}).get("cors_origins")
    return list(origins) if origins else ["http://localhost:3000"]


def create_app() -> FastAPI:
    app = FastAPI(title="Nova AI", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware, allow_origins=_cors_origins(),
        allow_methods=["*"], allow_headers=["*"])
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(goals_router)
    app.include_router(memory_router)
    app.include_router(safety_router)
    app.include_router(onboarding_router)
    app.include_router(sessions_router)
    app.include_router(tools_router)
    app.include_router(sync_router)
    app.include_router(proactive_router)
    app.include_router(longitudinal_router)
    app.include_router(admin_router)
    app.include_router(relationship_router)
    app.include_router(voice_router)
    app.include_router(messages_router)
    app.include_router(continuity_router)
    return app


app = create_app()
