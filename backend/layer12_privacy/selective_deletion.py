"""SC-2 — Selective Deletion (architecture doc §4).

Lets users make Nova forget — genuinely and surgically. The six deletion types each carry an undo
window and confirmation tier. Before anything is destroyed, ``dry_run_deletion`` computes the full
``CascadeImpactReport`` (which semantic facts, personality params, and longitudinal references are
affected) so the user sees the true scope. Execution secure-zeros content before removal and emits
a signed ``DeletionCertificate`` as cryptographic proof. Stores are duck-typed and injected.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from typing import Callable, Optional

from backend.layer12_privacy.schemas import (
    CascadeImpactReport,
    DELETION_CONFIRMATION_REQUIREMENTS,
    DELETION_UNDO_WINDOWS,
    DeletionCertificate,
    DeletionRequest,
    DeletionScope,
    DeletionType,
)


def create_deletion_request(
    user_id: str, deletion_type: str, scope: DeletionScope, now: Optional[datetime] = None,
) -> DeletionRequest:
    """Build a deletion request with its confirmation tier and undo window (architecture doc §4.1)."""
    now = now or datetime.utcnow()
    return DeletionRequest(
        user_id=user_id, deletion_type=deletion_type, scope=scope, requested_at=now,
        confirmation_required=DELETION_CONFIRMATION_REQUIREMENTS.get(deletion_type, "standard"),
        undo_window_expiry=now + DELETION_UNDO_WINDOWS.get(deletion_type, DELETION_UNDO_WINDOWS[
            DeletionType.SINGLE_MEMORY.value]),
        status="pending")


def resolve_scope(scope: DeletionScope, deletion_type: str, memory_store) -> list:
    """Resolve a scope to the concrete set of memory IDs to delete (architecture doc §4.3)."""
    if deletion_type == DeletionType.SINGLE_MEMORY.value:
        return [scope.memory_id] if scope.memory_id else []
    if deletion_type == DeletionType.FULL_WIPE.value:
        return [m.memory_id for m in memory_store.all()]
    if deletion_type == DeletionType.TOPIC_BASED.value:
        tags = set(scope.topic_tags or [])
        ids = []
        for m in memory_store.all():
            if tags & set(getattr(m, "topic_tags", []) or []):
                ids.append(m.memory_id)
            elif scope.person_name and getattr(m, "person_name", None) == scope.person_name:
                ids.append(m.memory_id)
        return ids
    if deletion_type == DeletionType.SEMANTIC_WIPE.value:
        return list(scope.semantic_fact_ids or [])
    if deletion_type == DeletionType.IDENTITY_MEMORY.value:
        return list(scope.identity_entry_ids or [])
    if deletion_type == DeletionType.LONGITUDINAL_DATA.value:
        return list(scope.chapter_ids or [])
    return []


def dry_run_deletion(
    request: DeletionRequest,
    memory_store,
    semantic_store=None,
    personality_store=None,
    longitudinal_store=None,
) -> CascadeImpactReport:
    """Compute the full cascade WITHOUT executing anything (architecture doc §4.4)."""
    target = set(resolve_scope(request.scope, request.deletion_type, memory_store))

    # target holds whatever resolve_scope returned for this deletion type -- a mix of plain
    # strings (the live SINGLE_MEMORY route path, "str(memory_id)") and UUID objects (e.g.
    # FULL_WIPE's memory_store.all()). Compare on string form so both agree with a real
    # SemanticMemory's supporting_episode_ids (a list[UUID] after deserialization).
    target_str = {str(t) for t in target}

    affected_facts = []
    if semantic_store is not None:
        for fact in semantic_store.all():
            # Layer 2's real SemanticMemory field is supporting_episode_ids/memory_id/statement --
            # this previously read derived_from_episodes/fact_id/fact_text, none of which exist on
            # the real schema (would have raised AttributeError the first time a real
            # semantic_store was ever passed in; see docs/POLISH_BACKLOG.md).
            supporting = list(getattr(fact, "supporting_episode_ids", []) or [])
            cited = [e for e in supporting if str(e) in target_str]
            if not cited:
                continue
            remaining = [e for e in supporting if str(e) not in target_str]
            if len(remaining) == 0:
                impact = "will_be_deleted"
            elif len(remaining) < 2:
                impact = "will_be_updated"
            else:
                impact = "will_be_flagged_for_review"
            affected_facts.append((fact.memory_id, fact.statement, impact))

    pv_will_change, pv_params = False, []
    if personality_store is not None:
        impact = personality_store.simulate_removal_impact(list(target))
        pv_will_change = getattr(impact, "max_delta", 0.0) > 0.05
        pv_params = getattr(impact, "affected_params", [])

    longitudinal_refs = []
    if longitudinal_store is not None:
        for s in longitudinal_store.all_weekly_summaries():
            # Layer 10's real WeeklySummary has no backing_episode_ids field at all (that field
            # only exists on RetrospectivePacket) -- this would have raised AttributeError the
            # first time a real longitudinal_store was passed in. The real per-summary episode
            # anchor is its significant moment's episode_ids.
            moment = getattr(s, "most_emotionally_significant_moment", None)
            episode_ids = list(getattr(moment, "episode_ids", []) or []) if moment else []
            refs = [e for e in episode_ids if str(e) in target_str]
            if refs:
                longitudinal_refs.append((s.summary_id, f"{len(refs)} reference(s) would be removed"))

    del_count = sum(1 for _, _, t in affected_facts if t == "will_be_deleted")
    no_stores_checked = semantic_store is None and personality_store is None and longitudinal_store is None
    if no_stores_checked:
        # Don't claim a cascade was computed when every cascade store was left unwired — an
        # unqualified "will also:" header with zero bullets reads as "nothing else affected"
        # when the truth is "nothing else was checked".
        summary = [f"Deleting {len(target)} memory/memories. (Cascade impact on facts, "
                   f"personality, and weekly summaries was not computed — no linked stores "
                   f"were provided for this check.)"]
    else:
        summary = [f"Deleting {len(target)} memory/memories will also:"]
        if del_count:
            summary.append(f"  • Remove {del_count} inferred fact(s) derived exclusively from these")
        if pv_will_change:
            summary.append("  • Recalculate your personality profile")
        if longitudinal_refs:
            summary.append(f"  • Update {len(longitudinal_refs)} weekly summary/summaries")
        if not (del_count or pv_will_change or longitudinal_refs):
            summary.append("  • Nothing else — no other data references these memories")

    request.affected_memory_ids = sorted(target)
    request.cascade_impacts = CascadeImpactReport(
        memories_deleted=len(target), semantic_facts_affected=affected_facts,
        personality_vector_will_change=pv_will_change, personality_params_affected=pv_params,
        longitudinal_references_to_update=longitudinal_refs,
        summary_human_readable="\n".join(summary))
    request.dry_run_completed = True
    return request.cascade_impacts


def _generate_certificate(
    deleted_ids: list, request_id: str, executed_at: datetime, sign_fn: Optional[Callable],
) -> DeletionCertificate:
    payload = {"request_id": request_id, "deleted_ids": sorted(deleted_ids),
               "deleted_count": len(deleted_ids), "executed_at": executed_at.isoformat()}
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    signer = sign_fn or (lambda h: hashlib.sha256((h + "device_key").encode()).hexdigest())
    signature = signer(payload_hash)
    token = base64.b64encode(json.dumps(
        {"payload_hash": payload_hash, "signature": signature,
         "timestamp": executed_at.isoformat()}).encode()).decode()
    return DeletionCertificate(
        request_id=request_id, deleted_count=len(deleted_ids), deleted_ids=sorted(deleted_ids),
        executed_at=executed_at, payload_hash=payload_hash, signature=signature, token=token)


def execute_deletion(
    request: DeletionRequest,
    memory_store,
    audit_log: Optional[list] = None,
    sign_fn: Optional[Callable] = None,
    now: Optional[datetime] = None,
) -> DeletionCertificate:
    """Execute a confirmed, dry-run-completed deletion with secure zeroing (architecture doc §4.3)."""
    if request.status != "confirmed" or not request.dry_run_completed:
        raise ValueError("deletion requires status='confirmed' and a completed dry run")
    now = now or datetime.utcnow()
    target = resolve_scope(request.scope, request.deletion_type, memory_store)

    deleted = []
    for mid in target:
        record = memory_store.get(mid)
        if record is None:
            continue
        # Zero whichever content field the record actually has (EpisodicMemory uses `summary`,
        # not `content`) — an empty string, not NUL padding: Postgres jsonb rejects \x00 in
        # strings, so a NUL-filled value would raise on the first real (non-SQLite) delete.
        zero_fields = {"embedding": None, "importance_score": 0.0}
        for field in ("content", "summary"):
            if hasattr(record, field):
                zero_fields[field] = ""
        memory_store.update(mid, zero_fields)       # secure zero before delete
        memory_store.delete(mid)
        deleted.append(mid)

    cert = _generate_certificate(deleted, request.request_id, now, sign_fn)
    request.status = "complete"
    request.executed_at = now
    request.deletion_certificate = cert.token
    if audit_log is not None:
        audit_log.append({"request_id": request.request_id, "deletion_type": request.deletion_type,
                          "memory_count": len(deleted), "certificate": cert.token,
                          "executed_at": now})
    return cert
