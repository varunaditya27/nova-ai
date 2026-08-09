"""Memory routes — read-only audit of what Nova has stored (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import (
    AuditQueryResultOut, AuditableFactOut, AuditableMemoryOut, CorrectionResultOut, IntegrityOut,
    MemoryAuditOut, MemoryAuditViewOut, MemoryCorrectionIn, MemoryDeletionOut, MemoryOut,
    SemanticOut,
)
from infra.db.audit_trail import PostgresAuditTrail
from infra.db.goal_store import PostgresGoalStore
from infra.db.memory_store import PostgresMemoryStore
from infra.db.privacy_audit import PostgresPrivacyAudit
from infra.db.longitudinal_store import PostgresLongitudinalStore
from infra.db.safety_record_store import PostgresSafetyRecordStore
from infra.db.safety_store import PostgresSafetyLog

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
    """Adapts PostgresMemoryStore to the duck-type dry_run_deletion/redact_cascade's semantic-facts
    cascade check expects (`.all()`, and `.get()`/`.update()` for real redaction)."""
    def __init__(self, store, user_id):
        self._s, self._u = store, user_id
    def all(self):
        return self._s.active_semantic(self._u)
    def get(self, mid):
        return self._s.get_semantic(mid)
    def update(self, mid, fields):
        self._s.update_semantic(mid, fields)


class _LongitudinalDeletionStore:
    """Adapts PostgresLongitudinalStore to the duck-type dry_run_deletion/redact_cascade's
    longitudinal cascade check expects (`.all_weekly_summaries()`, and `.get()`/`.update()` for
    real redaction)."""
    def __init__(self, store):
        self._s = store
    def all_weekly_summaries(self):
        return self._s.summaries(period="weekly")
    def get(self, summary_id):
        return next((s for s in self._s.summaries(period="weekly") if s.summary_id == summary_id),
                    None)
    def update(self, summary):
        self._s.save_summary(summary, period="weekly")


class _IdentityAuditStore:
    """Adapts PostgresMemoryStore to the `.all()` duck-type generate_audit_view's identity-beliefs
    read expects."""
    def __init__(self, store):
        self._s = store
    def all(self):
        return self._s.identity_beliefs()


class _SafetyAuditStore:
    """Adapts PostgresSafetyLog to the `.crisis_session_count()` duck-type generate_audit_view
    expects."""
    def __init__(self, store, user_id):
        self._s, self._u = store, user_id
    def crisis_session_count(self):
        return self._s.crisis_count(self._u)


class _GoalAuditStore:
    """Adapts PostgresGoalStore to the `.active_goal_count()` duck-type generate_audit_view
    expects."""
    def __init__(self, store):
        self._s = store
    def active_goal_count(self):
        return len(self._s.load_by_status(["active"]))


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


@router.get("/audit/full", response_model=MemoryAuditViewOut)
def memory_audit_full(state=Depends(get_state)):
    """Layer-12 SC-3 Memory Audit: the full transparency view — human-readable importance labels,
    semantic facts, identity beliefs, and crisis/goal counts (architecture doc §5.2). Distinct from
    the simpler `/memory/audit` above (episodic+semantic only, no labels/counts)."""
    from backend.layer12_privacy.memory_audit import generate_audit_view

    uid = state.default_user_id
    store = _store(state)
    try:
        view = generate_audit_view(
            uid, memory_store=_EpisodicDeletionStore(store, uid),
            semantic_store=_SemanticDeletionStore(store, uid),
            identity_store=_IdentityAuditStore(store),
            safety_store=_SafetyAuditStore(PostgresSafetyLog(state.session_factory), uid),
            goal_store=_GoalAuditStore(PostgresGoalStore(state.session_factory, uid)))
    except Exception:
        raise HTTPException(status_code=503, detail="memory audit temporarily unavailable")
    return MemoryAuditViewOut(
        user_id=str(view.user_id),
        generated_at=view.generated_at.isoformat() if view.generated_at else None,
        total_memory_count=view.total_memory_count,
        episodic=[AuditableMemoryOut(
            memory_id=str(e.memory_id),
            date_formed=e.date_formed.isoformat() if e.date_formed else None,
            human_readable_summary=e.human_readable_summary, importance_label=e.importance_label,
            topic_tags=list(e.topic_tags or []), emotion_at_formation=e.emotion_at_formation,
            reinforcement_count=e.reinforcement_count) for e in view.episodic],
        semantic=[AuditableFactOut(
            fact_id=f.fact_id, fact_text=f.fact_text, category=f.category,
            confidence=f.confidence, source_episode_ids=list(f.source_episode_ids or []),
            is_user_confirmed=f.is_user_confirmed) for f in view.semantic],
        identity=[AuditableFactOut(
            fact_id=f.fact_id, fact_text=f.fact_text, category=f.category,
            confidence=f.confidence, source_episode_ids=list(f.source_episode_ids or []),
            is_user_confirmed=f.is_user_confirmed) for f in view.identity],
        crisis_session_count=view.crisis_session_count, active_goal_count=view.active_goal_count)


@router.get("/audit/query", response_model=AuditQueryResultOut)
def memory_audit_query(q: str, state=Depends(get_state)):
    """Layer-12 SC-3 natural-language audit query — "what do you know about my job?" (architecture
    doc §5.3). Returns matching record ids; fetch full detail via GET /memory/{id}."""
    from backend.layer12_privacy.memory_audit import query as run_audit_query

    uid = state.default_user_id
    store = _store(state)
    try:
        result = run_audit_query(
            q, memory_store=_EpisodicDeletionStore(store, uid),
            semantic_store=_SemanticDeletionStore(store, uid),
            identity_store=_IdentityAuditStore(store))
    except Exception:
        raise HTTPException(status_code=503, detail="memory audit temporarily unavailable")
    ids = [str(getattr(r, "memory_id", getattr(r, "belief_id", ""))) for r in result.records]
    return AuditQueryResultOut(query=result.query, total_count=result.total_count,
                               intent_type=result.intent_type, memory_ids=ids)


@router.post("/{memory_id}/correct", response_model=CorrectionResultOut)
def correct_memory(memory_id: str, body: MemoryCorrectionIn, state=Depends(get_state)):
    """Layer-12 SC-3 Memory Correction: accept a user correction without debate (architecture doc
    §5.5). Six types — edit/downgrade/decontextualize/anchor/expire/confirm."""
    from datetime import date as date_cls
    from backend.layer12_privacy.correction_interface import apply_correction
    from backend.layer12_privacy.schemas import MemoryCorrectionRequest

    store = _store(state)
    expiry = date_cls.fromisoformat(body.expiry_date) if body.expiry_date else None
    req = MemoryCorrectionRequest(
        memory_id=memory_id, correction_type=body.correction_type, new_content=body.new_content,
        new_importance=body.new_importance, tags_to_remove=body.tags_to_remove, expiry_date=expiry)
    audit_log: list = []
    result = apply_correction(req, _EpisodicDeletionStore(store, state.default_user_id),
                              audit_log=audit_log)
    if result.success:
        PostgresPrivacyAudit(state.session_factory, state.default_user_id).append(
            "correct_memory", {"memory_id": memory_id, "correction_type": body.correction_type})
    return CorrectionResultOut(success=result.success, memory_id=result.memory_id,
                               correction_type=result.correction_type, detail=result.detail)


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
    cascade report checks semantic facts and weekly summaries for references to the deleted
    episode, and — per product decision 2026-08-09 — the affected facts/summaries are then
    genuinely redacted in place (references stripped, row kept), not just reported. No
    personality-vector store exists anywhere in this codebase to check, so that cascade stays
    permanently unreported, not silently wrong."""
    from backend.layer12_privacy.selective_deletion import (
        create_deletion_request, dry_run_deletion, execute_deletion, redact_cascade)
    from backend.layer12_privacy.schemas import DeletionScope, DeletionType

    uid = state.default_user_id
    store = _store(state)
    mem = store.get_episodic(memory_id)
    if mem is None or getattr(mem, "is_deleted", False):
        raise HTTPException(status_code=404, detail="memory not found")

    adapter = _EpisodicDeletionStore(store, uid)
    semantic_adapter = _SemanticDeletionStore(store, uid)
    longitudinal_adapter = _LongitudinalDeletionStore(
        PostgresLongitudinalStore(state.session_factory, uid))
    req = create_deletion_request(uid, DeletionType.SINGLE_MEMORY.value,
                                  DeletionScope(memory_id=str(memory_id)))
    report = dry_run_deletion(
        req, adapter, semantic_store=semantic_adapter, longitudinal_store=longitudinal_adapter)
    req.status = "confirmed"
    cert = execute_deletion(req, adapter)
    redact_cascade(report, cert.deleted_ids, semantic_store=semantic_adapter,
                   longitudinal_store=longitudinal_adapter)
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
