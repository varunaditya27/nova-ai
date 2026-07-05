"""Memory routes — read-only audit of what Nova has stored (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import MemoryAuditOut, MemoryOut, SemanticOut
from infra.db.memory_store import PostgresMemoryStore

router = APIRouter(prefix="/memory", tags=["memory"])


def _store(state):
    return PostgresMemoryStore(state.session_factory)


def _ep_out(m) -> MemoryOut:
    created = getattr(m, "created_at", None)
    return MemoryOut(memory_id=str(m.memory_id), summary=getattr(m, "summary", ""),
                     importance=getattr(m, "importance_score", 0.0),
                     created_at=created.isoformat() if created else None,
                     topic_tags=list(getattr(m, "topic_tags", []) or []))


def _sem_out(m) -> SemanticOut:
    return SemanticOut(memory_id=str(m.memory_id), statement=getattr(m, "statement", ""),
                       confidence=getattr(m, "confidence", 0.0))


@router.get("/audit", response_model=MemoryAuditOut)
def memory_audit(state=Depends(get_state)):
    uid = state.default_user_id
    store = _store(state)
    try:
        return MemoryAuditOut(
            episodic=[_ep_out(m) for m in store.active_episodic(uid)],
            semantic=[_sem_out(m) for m in store.active_semantic(uid)])
    except Exception:
        raise HTTPException(status_code=503, detail="memory temporarily unavailable")


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: str, state=Depends(get_state)):
    m = _store(state).get_episodic(memory_id)
    if m is None:
        raise HTTPException(status_code=404, detail="memory not found")
    return _ep_out(m)
