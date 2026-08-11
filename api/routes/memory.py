"""Memory routes — Layer 2: read-only audit of what Nova has stored (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import IntegrityOut, MemoryAuditOut, MemoryOut, SemanticOut
from infra.db.audit_trail import PostgresAuditTrail
from infra.db.memory_store import PostgresMemoryStore
from infra.db.privacy_audit import PostgresPrivacyAudit
from infra.db.safety_record_store import PostgresSafetyRecordStore

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


@router.get("/integrity", response_model=IntegrityOut)
def memory_integrity(state=Depends(get_state)):
    """Verify the tamper-evident hash chains (Layer-2 memory audit + Layer-11 safety record +
    Layer-12 privacy audit)."""
    uid = state.default_user_id
    try:
        audit_ok = PostgresAuditTrail(state.session_factory, uid).verify()
        privacy_ok = PostgresPrivacyAudit(state.session_factory, uid).verify()
        safety_ok = PostgresSafetyRecordStore(state.session_factory, uid).verify_chain()
    except Exception:
        raise HTTPException(status_code=503, detail="integrity check unavailable")
    ok = audit_ok and privacy_ok and safety_ok
    return IntegrityOut(status="INTACT" if ok else "TAMPER_DETECTED",
                        audit_chain_ok=audit_ok, privacy_chain_ok=privacy_ok,
                        safety_chain_ok=safety_ok)


@router.get("/search", response_model=list[MemoryOut])
def memory_search(q: str, limit: int = 5, state=Depends(get_state)):
    """Semantic ('AI') search over episodic memory — "the time I was scared". Embeds the query and
    asks the vector store for nearest episodes, hydrating from Postgres; degrades to a keyword scan
    over summaries when the vector store is cold/unavailable (distinct from /messages/search)."""
    uid = state.default_user_id
    store = _store(state)
    vs = getattr(state, "vector_store", None)
    limit = max(1, min(limit, 25))
    try:
        if vs is not None and q:
            emb = state.llm_clients["embed"].embed([q])[0]
            hits = vs.query("episodic", emb, n_results=limit, where={"user_id": str(uid)})
            out = []
            for h in hits or []:
                mem = store.get_episodic(h.get("id"))
                if mem is not None and not getattr(mem, "is_deleted", False):
                    out.append(_ep_out(mem))
            if out:
                return out
        # Fallback: keyword scan over active episodic summaries.
        ql = (q or "").lower()
        return [_ep_out(m) for m in store.active_episodic(uid)
                if ql in (getattr(m, "summary", "") or "").lower()][:limit]
    except Exception:
        raise HTTPException(status_code=503, detail="memory search unavailable")


@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: str, state=Depends(get_state)):
    m = _store(state).get_episodic(memory_id)
    # get_episodic returns raw rows (Layer-12 deletion needs them too); a logically-deleted memory
    # is a genuine 'forget' and must read as not-found — mirror the DELETE handler's is_deleted guard.
    if m is None or getattr(m, "is_deleted", False):
        raise HTTPException(status_code=404, detail="memory not found")
    return _ep_out(m)
