"""SC-2 — Selective Deletion (architecture doc §4).

Lets users make Nova forget — genuinely and surgically. The six deletion types each carry an undo
window and confirmation tier. Before anything is destroyed, ``dry_run_deletion`` computes the full
``CascadeImpactReport`` (which semantic facts, personality params, and longitudinal references are
affected) so the user sees the true scope. Execution secure-zeros content before removal and emits
a signed ``DeletionCertificate`` as cryptographic proof. Stores are duck-typed and injected.

Request building/scope resolution live in ``deletion_scope.py``; cascade dry-run/redaction live in
``deletion_cascade.py``; both re-exported here.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from typing import Callable, Optional

from backend.layer12_privacy.deletion_cascade import dry_run_deletion, redact_cascade
from backend.layer12_privacy.deletion_scope import create_deletion_request, resolve_scope
from backend.layer12_privacy.schemas import DeletionCertificate, DeletionRequest

__all__ = [
    "create_deletion_request", "resolve_scope", "dry_run_deletion", "redact_cascade",
    "execute_deletion",
]


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
