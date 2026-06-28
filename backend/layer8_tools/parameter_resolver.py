"""SC: Parameter Resolver (architecture doc §6).

When a tool intent is detected but parameters are incomplete, this component identifies the
gaps, optionally infers high-confidence values from context, and otherwise produces a single
natural clarifying question. The cardinal rule is **one question per turn** — never bombard
the user with a form. User input is lightly normalized (e.g. "tomorrow" → an ISO date).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.layer8_tools.schemas import Capability, ParameterGap, ToolIntent

# Friendly phrasing per common parameter; falls back to a generic question.
_QUESTION_TEMPLATES = {
    "title": "What should I call it?",
    "start": "When should the start time be?",
    "due": "When is it due?",
    "to": "Who should I send it to?",
    "body": "What would you like it to say?",
    "content": "What should the note say?",
    "query": "What should I search for?",
}


def detect_parameter_gaps(intent: ToolIntent, capability: Capability) -> list[ParameterGap]:
    """Return a gap for each required parameter that is absent or empty (§6.2)."""
    params = intent.parameters or {}
    gaps: list[ParameterGap] = []
    for name in capability.required_params:
        if name not in params or params[name] in (None, ""):
            gaps.append(ParameterGap(parameter_name=name,
                                     description=_QUESTION_TEMPLATES.get(name, name)))
    return gaps


def generate_clarification_question(gap: ParameterGap) -> str:
    """A single natural question for one gap (§6.3)."""
    base = _QUESTION_TEMPLATES.get(gap.parameter_name)
    if base:
        return f"{base} (need: {gap.parameter_name})"
    return f"Could you tell me the {gap.parameter_name}?"


def next_clarification(intent: ToolIntent, capability: Capability) -> Optional[str]:
    """The one question to ask this turn, or None if nothing is missing (§6.3).

    Required params are asked in declaration order — the most critical first.
    """
    gaps = detect_parameter_gaps(intent, capability)
    if not gaps:
        return None
    return generate_clarification_question(gaps[0])


def resolve_parameter(gap: ParameterGap, user_response: str, now: Optional[datetime] = None) -> str:
    """Normalize a user's answer into a parameter value (§6.4)."""
    now = now or datetime.utcnow()
    text = (user_response or "").strip()
    low = text.lower()
    relative = {"today": 0, "tomorrow": 1, "the day after tomorrow": 2}
    if low in relative:
        return (now + timedelta(days=relative[low])).strftime("%Y-%m-%dT%H:%M")
    return text


def resolve_from_context(
    intent: ToolIntent,
    capability: Capability,
    infer_fn: Callable[[str, str], tuple],
    context: str = "",
    threshold: float = 0.85,
) -> ToolIntent:
    """Fill missing params from context when inference confidence clears the bar (§6.5).

    ``infer_fn(parameter_name, context) -> (value, confidence)``. Only values at or above
    ``threshold`` are auto-filled; everything else is left for a clarifying question.
    """
    for gap in detect_parameter_gaps(intent, capability):
        try:
            value, confidence = infer_fn(gap.parameter_name, context)
        except Exception:
            continue
        if value not in (None, "") and confidence >= threshold:
            intent.parameters[gap.parameter_name] = value
    intent.parameters_missing = [g.parameter_name
                                 for g in detect_parameter_gaps(intent, capability)]
    return intent
