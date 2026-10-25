"""SC-1 keyword-based intent routing fallback (architecture doc §5).

Split out of ``tool_manager.py``: the conservative (tool, operation) keyword rules used
both as the deterministic fallback when no ``intent_fn`` is injected, and to constrain
the LLM param-extractor (which only enriches parameters, never re-routes).
"""

from __future__ import annotations

import re
from typing import Optional

from backend.layer8_tools.schemas import ActionType, ToolIntent

# A tool fires only on a *request addressed to Nova* — an imperative or "can you …" opener — never
# on a bare keyword: "my meeting stresses me out" or "that song reminded me of my dad" are
# conversation, and hijacking them into a tool form would derail exactly the moments that matter.
_REQUEST_OPENER = (r"^\W*(?:(?:hey |hi )?nova\W+)?(?:(?:i need|i want|i'd like|i would like) you to |"
                   r"(?:can|could|would|will) you )?(?:please |pls )?")


def _request(verbs: str, rest: str = "") -> re.Pattern:
    return re.compile(_REQUEST_OPENER + r"(?:" + verbs + r")\b" + rest, re.I)


_KEYWORD_RULES = [
    (_request(r"search|google|look up|find online"), "web_search", "search"),
    (re.compile(r"\bremind me (?:to|about|that|of|at|in|on|tomorrow|tonight|next|every)\b|"
                r"\b(?:set|create|add) (?:a |an )?reminder\b", re.I), "reminders", "create_reminder"),
    (_request(r"email"), "email", "draft"),
    (_request(r"send|write|draft|compose", r"(?: an?| the| my| quick)* e-?mail\b"), "email", "draft"),
    (_request(r"schedule|book|set up|add|put|create", r".*\b(?:calendar|meeting|appointment|event|call)\b"),
     "calendar", "create_event"),
    (_request(r"take a note|make a note|jot (?:this |that )?down|write (?:this |that )?down"),
     "notes", "create_note"),
]


def keyword_route(message: str) -> Optional[tuple[str, str]]:
    """Conservative (tool, operation) routing — the low-false-positive gate shared by the
    deterministic fallback and the LLM param-extractor (which only enriches, never re-routes)."""
    for pattern, tool, operation in _KEYWORD_RULES:
        if pattern.search(message or ""):
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
