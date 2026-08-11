"""SC-1 keyword-based intent routing fallback (architecture doc §5).

Split out of ``tool_manager.py``: the conservative (tool, operation) keyword rules used
both as the deterministic fallback when no ``intent_fn`` is injected, and to constrain
the LLM param-extractor (which only enriches parameters, never re-routes).
"""

from __future__ import annotations

from typing import Optional

from backend.layer8_tools.schemas import ActionType, ToolIntent

# Keyword → (tool, operation) fallback when no intent_fn is supplied.
_KEYWORD_RULES = [
    (("search", "look up", "google", "find online"), "web_search", "search"),
    (("remind me", "reminder", "remind"), "reminders", "create_reminder"),
    (("send email", "email", "send a mail"), "email", "draft"),
    (("schedule", "calendar", "add event", "meeting", "appointment"), "calendar", "create_event"),
    (("take a note", "make a note", "jot down", "write down", "note that"), "notes", "create_note"),
]


def keyword_route(message: str) -> Optional[tuple[str, str]]:
    """Conservative (tool, operation) routing from keywords — the low-false-positive gate shared by
    the deterministic fallback and the LLM param-extractor (which only enriches, never re-routes)."""
    low = (message or "").lower()
    for keywords, tool, operation in _KEYWORD_RULES:
        if any(kw in low for kw in keywords):
            return tool, operation
    return None


def extract_search_query(message: str) -> str:
    """Deterministic web-search query extraction (strip the lead-in marker)."""
    low = (message or "").lower()
    for marker in ("search for ", "look up ", "search "):
        if marker in low:
            return message[low.index(marker) + len(marker):].strip()
    return (message or "").strip()


def coerce_intent(raw) -> Optional[ToolIntent]:
    """Normalize an injected ``intent_fn``'s raw output (dict or ToolIntent) to a ToolIntent."""
    if raw is None or isinstance(raw, ToolIntent):
        return raw
    if isinstance(raw, dict) and raw.get("tool_name"):
        return ToolIntent(
            tool_name=raw["tool_name"], operation=raw.get("operation", ""),
            action_type=raw.get("action_type", ActionType.READ.value),
            parameters=raw.get("parameters", {}), confidence=raw.get("confidence", 0.0),
            raw_text=raw.get("raw_text", ""))
    return None


def keyword_intent(message: str) -> Optional[ToolIntent]:
    """The deterministic fallback ToolIntent when no intent_fn is injected."""
    route = keyword_route(message)
    if route is None:
        return None
    tool, operation = route
    params = {"query": extract_search_query(message)} if tool == "web_search" else {}
    return ToolIntent(tool_name=tool, operation=operation, parameters=params,
                      confidence=0.5, raw_text=message)
