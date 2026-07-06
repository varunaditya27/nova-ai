"""LLM-backed tool intent: keyword-gated routing + small-model parameter extraction.

Tool *routing* stays on the conservative keyword rules (a tool only fires when the phrasing already
matched a keyword — no new false positives that could hijack normal conversation). A small, fast
model (e.g. gemma2:2b) then fills the *parameters* the routed capability declares, so SOFT/HARD
actions form a real confirmation instead of asking one clarification per turn forever. Any LLM/JSON
failure degrades to the deterministic keyword params — never worse than the offline fallback.

The result is a plain dict consumed by ``ToolManager._coerce_intent`` (which needs ``tool_name``).
"""
from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from backend.layer8_tools.tool_manager import extract_search_query, keyword_route

logger = logging.getLogger("nova.layer8")

_PROMPT = (
    "You extract structured parameters for a tool action from a user's message.\n"
    'The action is "{tool}.{operation}". Extract ONLY these parameters if the message states them: '
    "{params}.\n"
    "Return ONLY a JSON object mapping those exact keys to string values. Omit any key the message "
    "does not state. Never invent values.\n"
    'Message: "{message}"\nJSON:'
)


def make_llm_intent_fn(
    complete_fn: Callable[[str], str],
    required_params_for: Callable[[str, str], list],
) -> Callable[[str], Optional[dict]]:
    """Build a ``ToolManager`` intent_fn that routes by keyword and fills params via ``complete_fn``.

    ``required_params_for(tool, operation)`` returns the capability's required parameter names (wired
    from the live plugin registry) so the model is asked for exactly the keys the resolver needs.
    """
    def _intent(message: str) -> Optional[dict]:
        route = keyword_route(message or "")
        if route is None:
            return None                                  # not a tool turn — LLM never consulted
        tool, operation = route

        # Deterministic seed: guarantees web-search never regresses below keyword extraction.
        params: dict = {}
        if tool == "web_search":
            params["query"] = extract_search_query(message)

        required = required_params_for(tool, operation) or []
        missing = [p for p in required if p not in params]
        if missing:
            try:
                from infra.llm.json_extract import extract_json
                prompt = _PROMPT.format(tool=tool, operation=operation,
                                        params=", ".join(required), message=message)
                raw = json.loads(extract_json(complete_fn(prompt)))
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        if k in required and v not in (None, "", []):
                            params[k] = str(v).strip()
            except Exception:
                logger.exception("llm tool-intent param extraction failed; using keyword params")

        return {"tool_name": tool, "operation": operation, "parameters": params,
                "confidence": 0.7, "raw_text": message}
    return _intent
