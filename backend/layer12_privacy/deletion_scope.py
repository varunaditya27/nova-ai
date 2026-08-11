"""SC-2 request building + scope resolution (architecture doc §4.1, §4.3).

Split out of ``selective_deletion.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.layer12_privacy.schemas import (
    DELETION_CONFIRMATION_REQUIREMENTS,
    DELETION_UNDO_WINDOWS,
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
            matched = bool(tags & set(getattr(m, "topic_tags", []) or []))
            if not matched and scope.person_name:
                matched = getattr(m, "person_name", None) == scope.person_name
            if matched and scope.date_range:
                created = getattr(m, "created_at", None)
                created_date = created.date() if isinstance(created, datetime) else created
                start, end = scope.date_range
                matched = created_date is not None and start <= created_date <= end
            if matched:
                ids.append(m.memory_id)
        return ids
    if deletion_type == DeletionType.SEMANTIC_WIPE.value:
        return list(scope.semantic_fact_ids or [])
    if deletion_type == DeletionType.IDENTITY_MEMORY.value:
        return list(scope.identity_entry_ids or [])
    if deletion_type == DeletionType.LONGITUDINAL_DATA.value:
        return list(scope.chapter_ids or [])
    return []
