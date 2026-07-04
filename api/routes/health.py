"""Health endpoints — liveness (compose healthcheck) and readiness (DB probe)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from api.dependencies import get_state

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response, state=Depends(get_state)) -> dict:
    try:
        with state.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        response.status_code = 503
        return {"status": "not_ready", "component": "postgres", "detail": str(exc)[:200]}
    return {"status": "ready"}
