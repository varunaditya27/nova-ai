"""Memory routes — read-only audit of what Nova has stored (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import IntegrityOut, MemoryAuditOut, MemoryDeletionOut, MemoryOut, SemanticOut
from infra.db.audit_trail import PostgresAuditTrail
from infra.db.memory_store import PostgresMemoryStore
from infra.db.privacy_audit import PostgresPrivacyAudit
from infra.db.longitudinal_store import PostgresLongitudinalStore
from infra.db.safety_record_store import PostgresSafetyRecordStore

router = APIRouter(prefix="/memory", tags=["memory"])


def _store(state):
    return PostgresMemoryStore(state.session_factory)


class _EpisodicDeletionStore:
    """Adapts PostgresMemoryStore to the get/update/delete/all duck-type Layer-12 deletion expects."""
    def __init__(self, store, user_id):
        self._s, self._u = store, user_id
    def all(self):
        return self._s.active_episodic(self._u)
    def get(self, mid):
        return self._s.get_episodic(mid)
    def update(self, mid, fields):
        self._s.update_episodic(mid, fields)
    def delete(self, mid):
        self._s.delete_episodic(mid)


class _SemanticDeletionStore:
    """Adapts PostgresMemoryStore to the `.all()` duck-type dry_run_deletion's semantic-facts
    cascade check expects."""
    def __init__(self, store, user_id):
        self._s, self._u = store, user_id
    def all(self):
        return self._s.active_semantic(self._u)


class _LongitudinalDeletionStore:
    """Adapts PostgresLongitudinalStore to the `.all_weekly_summaries()` duck-type
    dry_run_deletion's longitudinal cascade check expects."""
    def __init__(self, store):
        self._s = store
    def all_weekly_summaries(self):
        return self._s.summaries(period="weekly")


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
    # get_episodic returns raw rows (Layer-12 deletion needs them); a logically-deleted memory is a
    # genuine 'forget' and must read as not-found — mirror the DELETE handler's is_deleted guard.
    if m is None or getattr(m, "is_deleted", False):
        raise HTTPException(status_code=404, detail="memory not found")
    return _ep_out(m)


@router.delete("/{memory_id}", response_model=MemoryDeletionOut)
def delete_memory(memory_id: str, state=Depends(get_state)):
    """Layer-12 selective deletion of a single memory: genuine 'forget' (unrecallable + content
    zeroed), a signed deletion certificate, and a tamper-evident privacy-audit entry. The dry-run
    cascade report now genuinely checks semantic facts and weekly summaries for references to the
    deleted episode (previously always reported "not computed" — semantic_store/longitudinal_store
    were never passed). Execution itself still only mutates the primary episodic store — actually
    updating/removing the affected semantic facts or longitudinal summaries is a separate,
    undecided feature (see docs/POLISH_BACKLOG.md); no personality-vector store exists anywhere in
    this codebase to check, so that cascade stays permanently unreported, not silently wrong."""
    from backend.layer12_privacy.selective_deletion import (
        create_deletion_request, dry_run_deletion, execute_deletion)
    from backend.layer12_privacy.schemas import DeletionScope, DeletionType

    uid = state.default_user_id
    store = _store(state)
    mem = store.get_episodic(memory_id)
    if mem is None or getattr(mem, "is_deleted", False):
        raise HTTPException(status_code=404, detail="memory not found")

    adapter = _EpisodicDeletionStore(store, uid)
    req = create_deletion_request(uid, DeletionType.SINGLE_MEMORY.value,
                                  DeletionScope(memory_id=str(memory_id)))
    report = dry_run_deletion(
        req, adapter, semantic_store=_SemanticDeletionStore(store, uid),
        longitudinal_store=_LongitudinalDeletionStore(
            PostgresLongitudinalStore(state.session_factory, uid)))
    req.status = "confirmed"
    cert = execute_deletion(req, adapter)
    vs = getattr(state, "vector_store", None)
    if vs is not None:   # drop it from the ANN index too (best-effort — audit row remains)
        try:
            vs.delete("episodic", [str(memory_id)])
        except Exception:
            pass
    PostgresPrivacyAudit(state.session_factory, uid).append(
        "delete_memory", {"memory_id": str(memory_id), "certificate": cert.token})
    return MemoryDeletionOut(deleted=cert.deleted_count, memory_id=str(memory_id),
                             certificate=cert.token, cascade=report.summary_human_readable)
