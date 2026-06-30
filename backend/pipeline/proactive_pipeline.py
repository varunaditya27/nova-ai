"""Proactive pipeline — background outreach (Layer 6), independent of user-initiated turns.

Triggered by the scheduler (~every 30 min). Evaluates queued proactive candidates, applies the
timing/delivery gates, generates a message, and delivers via Layer 9 — then the response tracker
monitors engagement. Pure orchestration over injected steps; suppressed entirely while a user is
in cold start (Layer 13 sets proactivity to observe-only).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def run_proactive_check(evaluate: Callable, gate: Callable, generate: Callable,
                        deliver: Callable, *, cold_start_active: bool = False) -> list:
    """Evaluate candidates, gate, generate and deliver. Returns delivered notification events."""
    if cold_start_active:
        return []                                  # Layer 13 overlay: no proactive reaches yet
    delivered = []
    for candidate in evaluate() or []:
        try:
            if not gate(candidate):
                continue
            message = generate(candidate)
            delivered.append(deliver(candidate, message))
        except Exception:
            logger.exception("proactive candidate %r failed; skipping", candidate)
    return delivered
