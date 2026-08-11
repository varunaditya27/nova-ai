"""Layer 3 §12 hard-rule helpers: fail-safe sub-component execution + crisis alerting."""

from __future__ import annotations

from backend.layer3_reasoning.schemas import CrisisAlert, EmotionClassification


def emit_alert(alert_fn, emotion: EmotionClassification, message: str, source: str) -> None:
    alert_fn(CrisisAlert(
        crisis_confidence=emotion.crisis_confidence,
        crisis_type=emotion.crisis_type,
        message_excerpt=message[:120],
        source=source,
    ))


def safe(fn, fallback):
    """Run a sub-component; on any failure return the fallback (architecture doc §12)."""
    try:
        return fn()
    except Exception:
        return fallback
