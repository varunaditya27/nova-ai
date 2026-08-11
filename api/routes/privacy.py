"""Privacy routes — Layer 12: transparency audit, correction, and selective deletion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import (
    AuditQueryResultOut, AuditableFactOut, AuditableMemoryOut, CorrectionResultOut,
    MemoryAuditViewOut, MemoryCorrectionIn, MemoryDeletionOut,
)
from infra.db.goal_store import PostgresGoalStore
from infra.db.longitudinal_store import PostgresLongitudinalStore
from infra.db.memory_store import PostgresMemoryStore
from infra.db.privacy_audit import PostgresPrivacyAudit
from infra.db.safety_store import PostgresSafetyLog

from .privacy_adapters import (
    EpisodicDeletionStore as _EpisodicDeletionStore,
    GoalAuditStore as _GoalAuditStore,
    IdentityAuditStore as _IdentityAuditStore,
    LongitudinalDeletionStore as _LongitudinalDeletionStore,
    SafetyAuditStore as _SafetyAuditStore,
    SemanticDeletionStore as _SemanticDeletionStore,
)

router = APIRouter(prefix="/memory", tags=["privacy"])


def _store(state):
    return PostgresMemoryStore(state.session_factory)


@router.get("/audit/full", response_model=MemoryAuditViewOut)
def memory_audit_full(state=Depends(get_state)):
    """Layer-12 SC-3 Memory Audit: the full transparency view — human-readable importance labels,
    semantic facts, identity beliefs, and crisis/goal counts (architecture doc §5.2). Distinct from
    the simpler `/memory/audit` (Layer 2, episodic+semantic only, no labels/counts)."""
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
