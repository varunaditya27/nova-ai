"""Post-turn state update orchestration (fire-and-forget; never blocks the user).

Runs after the response is delivered. Sequences the write path across layers: Layer 2 episodic
write + reinforcement + consolidation trigger, Layer 4 personality drift, Layer 5 relationship
updates, Layer 7 goal progress, Layer 10 longitudinal data, Layer 12 audit log. Each writer is
injected so this stays pure orchestration; a failing writer is logged and skipped so post-turn
bookkeeping can never corrupt state or affect the (already delivered) response.
"""

from __future__ import annotations

import logging
from typing import Callable, Sequence

logger = logging.getLogger(__name__)


def run_state_update(ctx, writers: Sequence[Callable]) -> int:
    """Run each post-turn writer over the turn context. Returns the count that succeeded."""
    succeeded = 0
    for writer in writers:
        try:
            writer(ctx)
            succeeded += 1
        except Exception:  # post-turn writes must never affect the delivered response
            logger.exception("post-turn writer %r failed; skipping", getattr(writer, "__name__", writer))
    return succeeded
