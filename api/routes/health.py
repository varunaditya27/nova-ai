"""Health endpoints — liveness (compose healthcheck) and readiness (DB probe)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response

from api.dependencies import get_state

logger = logging.getLogger("nova.api")
router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response, state=Depends(get_state)) -> dict:
    try:
        with state.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception:
        # Log the detail server-side; never return internal error text to the client
        # (it can leak DSNs/hostnames/stack info to an unauthenticated caller).
        logger.exception("readiness probe failed: postgres unreachable")
        response.status_code = 503
        return {"status": "not_ready", "component": "postgres"}
    return {"status": "ready"}
