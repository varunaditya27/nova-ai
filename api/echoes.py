"""Project the memories Nova recalled this turn into UI 'echoes' (gpt-chat-reference Principle 7).

Layer-2 recall returns ``ScoredMemory`` wrappers (``.memory`` is the episode, ``.fuzzy_temporal_label``
is the human 'when' — e.g. "a few weeks ago", already computed per the no-raw-timestamps invariant).
This unwraps them defensively so it also accepts a bare memory object (used in tests).
"""
from __future__ import annotations


def _text(memory) -> str:
    for attr in ("summary", "content", "text", "statement"):
        val = getattr(memory, attr, "") or ""
        if val:
            return val
    return ""


def project_echoes(recalled, limit: int = 3) -> list[dict]:
    echoes: list[dict] = []
    for item in (recalled or []):
        memory = getattr(item, "memory", item)                 # unwrap ScoredMemory, else use as-is
        summary = _text(memory)
        if not summary:
            continue                                           # inferred-only / empty → skip
        when = getattr(item, "fuzzy_temporal_label", "") or ""
        created = getattr(memory, "created_at", None)
        echoes.append({
            "summary": summary[:200],
            "when": when or None,
            "created_at": created.isoformat() if hasattr(created, "isoformat") else None,
        })
        if len(echoes) >= limit:
            break
    return echoes
