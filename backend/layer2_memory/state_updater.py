"""State Updater — the write path (architecture doc §12).

All writes to Layer 2 go through here, and it runs *after* the conversation turn completes.
Layer 2 is read-only during inference: memory is never mutated mid-turn, so Nova cannot
"learn" something and contradict itself in the same response.

Every store/audit write is best-effort: an audit write failure must never block the state
update or the conversation (§15).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
from uuid import UUID

from . import memory_strength as ms
from .audit_trail import AuditTrail
from .schemas import (
    AuditEvent,
    AuditEventType,
    EmotionVector,
    EpisodicMemory,
    ScoredMemory,
    ShortTermMemoryBuffer,
    UserWorldModel,
)

# (stm_buffer, emotion) → newly extracted episodic memories. Production wires the Episodic
# Memory Extractor (LLM summarization); tests inject a deterministic function.
EpisodeExtractor = Callable[[ShortTermMemoryBuffer, EmotionVector], list[EpisodicMemory]]

# (existing UWM or None) → updated UWM to persist, or None to skip this turn. Production wires
# real per-turn signal extraction + merge (backend/layer2_memory/uwm_updater.py); without an
# injected updater, step 3 below falls back to a version-only bump on an existing row (its
# original behavior, kept so old callers are unaffected).
UWMUpdater = Callable[[Optional[UserWorldModel]], Optional[UserWorldModel]]


@dataclass
class StateUpdateResult:
    episodes_created: int = 0
    memories_reinforced: int = 0
    uwm_updated: bool = False


def _safe_audit(audit: AuditTrail, event: AuditEvent) -> None:
    """Append to the audit trail; swallow failures so they never block the update (§15)."""
    try:
        audit.append(event)
    except Exception:  # noqa: BLE001 - log-to-error-file in production
        pass


def state_updater(
    user_id: UUID,
    session_id: UUID,
    stm_buffer: ShortTermMemoryBuffer,
    store,
    audit: AuditTrail,
    emotion: EmotionVector,
    now: datetime,
    extractor_fn: EpisodeExtractor,
    *,
    last_recall: Optional[list[ScoredMemory]] = None,
    used_memory_ids: Optional[set] = None,
    uwm_updater_fn: Optional[UWMUpdater] = None,
) -> StateUpdateResult:
    """Run the post-turn write path (§12.2). Returns a summary of what was written."""
    result = StateUpdateResult()
    used_memory_ids = used_memory_ids or set()

    # 1. Episodic memory extraction from STM.
    for episode in extractor_fn(stm_buffer, emotion):
        episode.user_id = episode.user_id or user_id
        episode.session_id = episode.session_id or session_id
        episode.created_at = episode.created_at or now
        store.save_episodic(episode)
        result.episodes_created += 1
        _safe_audit(audit, AuditEvent(
            user_id=user_id, timestamp=now, event_type=AuditEventType.MEMORY_CREATED,
            memory_id=episode.memory_id, session_id=session_id,
            reason="Episodic memory extracted from session", triggered_by="state_updater",
        ))

    # 2. Reinforce recalled memories that were actually used in the response.
    for scored in last_recall or []:
        mem = scored.memory
        if getattr(mem, "memory_id", None) in used_memory_ids:
            signal = max(0.0, min(1.0, scored.effective_score))
            mem.S_current = ms.reinforce(mem.S_current, signal)
            mem.reinforcement_count += 1
            store.save_episodic(mem)  # persist strength through the store (store-agnostic)
            result.memories_reinforced += 1
            _safe_audit(audit, AuditEvent(
                user_id=user_id, timestamp=now, event_type=AuditEventType.MEMORY_REINFORCED,
                memory_id=mem.memory_id, session_id=session_id, score_at_event=signal,
                reason="Memory used in response → reinforced", triggered_by="state_updater",
            ))

    # 3. Update the User World Model. With an injected updater (real per-turn signal extraction
    # + merge — backend/layer2_memory/uwm_updater.py — is the caller's job, this function stays
    # storage-agnostic), it can also create the first row for a user who has none yet. Without
    # one, fall back to the original version-only bump on an existing row.
    uwm = store.load_uwm(user_id)
    updated_uwm = uwm_updater_fn(uwm) if uwm_updater_fn is not None else None
    if updated_uwm is not None:
        store.save_uwm(updated_uwm)
        result.uwm_updated = True
        _safe_audit(audit, AuditEvent(
            user_id=user_id, timestamp=now, event_type=AuditEventType.UWM_UPDATED,
            session_id=session_id, reason="UWM updated after session",
            triggered_by="state_updater",
        ))
    elif uwm_updater_fn is None and uwm is not None:
        uwm.update_version += 1
        uwm.last_updated_at = now
        store.save_uwm(uwm)
        result.uwm_updated = True
        _safe_audit(audit, AuditEvent(
            user_id=user_id, timestamp=now, event_type=AuditEventType.UWM_UPDATED,
            session_id=session_id, reason="UWM updated after session",
            triggered_by="state_updater",
        ))

    return result
