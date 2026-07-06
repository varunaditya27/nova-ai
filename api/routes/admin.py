"""Admin routes — manually trigger a background job (single-user, no auth).

Lets each scheduler job run on demand (ops + testing) without waiting for its cadence. The job
runs synchronously against the live AppState and its result summary is returned.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import JobRunOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/jobs/{name}", response_model=JobRunOut)
def run_job(name: str, state=Depends(get_state)):
    from background.scheduler import JOBS, run_job as _run

    if name not in JOBS:
        raise HTTPException(status_code=404, detail=f"unknown job '{name}'")
    try:
        result = _run(state, name)
    except Exception:
        raise HTTPException(status_code=500, detail="job failed")
    return JobRunOut(job=name, result=result)
