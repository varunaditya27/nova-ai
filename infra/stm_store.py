"""In-process store for Layer 2's Short-Term Memory buffer (backend/layer2_memory/stm.py).

The architecture doc specifies STM as ephemeral, RAM-only, per-session state (never persisted to
disk) — the sliding window that lets `add_turn`/`should_promote` actually accumulate turns and
evict/promote them across the many separate ``POST /chat`` requests that make up one session.
A plain in-process dict keyed by session_id satisfies that spec exactly for this codebase's
single-process, single-user deployment: it survives across requests within the process's
lifetime and is correctly wiped — not corrupted, not silently stale — on restart.

Distinct from the orchestrator's per-request ``TurnContext`` (intermediate layer outputs within a
single ``/chat`` call, never a separate cache object) and from Layer 2's persisted stores
(episodic/semantic/etc., which live in Postgres). This module holds exactly one thing:
``ShortTermMemoryBuffer`` objects.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional
from uuid import UUID

from backend.layer2_memory.schemas import ShortTermMemoryBuffer

# Single-user deployment, but session_id is minted fresh per browser tab/reload (no persisted
# client-side session), so distinct session_keys can accumulate over a long process lifetime.
# Bounded LRU eviction keeps this from growing without limit; an evicted session's un-promoted
# turns are simply lost, same as a process restart (§3.1's "ephemeral" is the point).
_MAX_SESSIONS = 200


class InProcessSTMStore:
    """Thread-safe in-memory ``{session_key: ShortTermMemoryBuffer}`` map, LRU-bounded."""

    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._buffers: "OrderedDict[str, ShortTermMemoryBuffer]" = OrderedDict()
        self._lock = threading.Lock()
        self._max_sessions = max_sessions

    def get_or_create(self, session_key: str, user_id: UUID) -> ShortTermMemoryBuffer:
        with self._lock:
            buf = self._buffers.get(session_key)
            if buf is None:
                buf = ShortTermMemoryBuffer(session_id=session_key, user_id=user_id)
            self._buffers[session_key] = buf   # (re)insert → most-recently-used
            self._buffers.move_to_end(session_key)
            self._evict_oldest_locked()
            return buf

    def save(self, session_key: str, buffer: ShortTermMemoryBuffer) -> None:
        with self._lock:
            self._buffers[session_key] = buffer
            self._buffers.move_to_end(session_key)
            self._evict_oldest_locked()

    def get(self, session_key: str) -> Optional[ShortTermMemoryBuffer]:
        with self._lock:
            return self._buffers.get(session_key)

    def _evict_oldest_locked(self) -> None:
        while len(self._buffers) > self._max_sessions:
            self._buffers.popitem(last=False)
