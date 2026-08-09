"""SC-3 — Memory Correction Interface (architecture doc §5.5).

Lets users correct Nova's understanding of them. Corrections are taken seriously and accepted
without debate. Six types: edit (with embedding recompute), downgrade, decontextualize, anchor
(maximum persistence), expire (future auto-deletion), and confirm. Every correction is logged to
the audit trail. Stores and the embedder are duck-typed / injected.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer12_privacy.schemas import (
    CorrectionResult,
    MemoryCorrectionRequest,
    MemoryCorrectionType,
)

_DOWNGRADE_SCORES = {"Low": 0.20, "Medium": 0.50}


def apply_correction(
    request: MemoryCorrectionRequest,
    memory_store,
    embed_fn: Optional[Callable] = None,
    audit_log: Optional[list] = None,
) -> CorrectionResult:
    """Apply a user correction to a memory object (architecture doc §5.5)."""
    record = memory_store.get(request.memory_id)
    if record is None:
        return CorrectionResult(success=False, memory_id=request.memory_id,
                                correction_type=request.correction_type, detail="memory not found")

    ctype = request.correction_type
    if ctype == MemoryCorrectionType.EDIT.value:
        # Layer 2's real EpisodicMemory field is `summary`, not `content` -- set both so this
        # works against either shape (mirrors selective_deletion.execute_deletion's secure-zero,
        # which does the same for the same reason).
        fields = {"content": request.new_content, "summary": request.new_content,
                  "is_user_confirmed": True, "last_corrected_at": datetime.utcnow()}
        if embed_fn is not None:
            fields["embedding"] = embed_fn(request.new_content)
        memory_store.update(request.memory_id, fields)

    elif ctype == MemoryCorrectionType.DOWNGRADE.value:
        new_score = _DOWNGRADE_SCORES.get(request.new_importance, 0.20)
        current = getattr(record, "importance_score", new_score)
        memory_store.update(request.memory_id,
                            {"importance_score": min(current, new_score), "is_user_downgraded": True})

    elif ctype == MemoryCorrectionType.DECONTEXTUALIZE.value:
        remove = set(request.tags_to_remove or [])
        kept = [t for t in getattr(record, "topic_tags", []) if t not in remove]
        memory_store.update(request.memory_id, {"topic_tags": kept})

    elif ctype == MemoryCorrectionType.ANCHOR.value:
        memory_store.update(request.memory_id, {
            "decay_rate": 0.0, "is_anchored": True,
            "importance_score": max(getattr(record, "importance_score", 0.0), 0.95)})

    elif ctype == MemoryCorrectionType.EXPIRE.value:
        memory_store.update(request.memory_id, {"auto_expiry_date": request.expiry_date})

    elif ctype == MemoryCorrectionType.CONFIRM.value:
        memory_store.update(request.memory_id, {"is_user_confirmed": True})

    else:
        return CorrectionResult(success=False, memory_id=request.memory_id,
                                correction_type=ctype, detail="unknown correction type")

    if audit_log is not None:
        audit_log.append({"memory_id": request.memory_id, "correction_type": ctype,
                          "at": datetime.utcnow()})
    return CorrectionResult(success=True, memory_id=request.memory_id, correction_type=ctype)
