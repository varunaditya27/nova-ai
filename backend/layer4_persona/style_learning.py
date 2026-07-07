"""Per-user persona-parameter learning (Layer 4/5).

Observes the user's communication style each turn and nudges the persisted ``RelationshipState``
calibration params — verbosity (``response_length_preference``), ``formality_preference``,
``question_tolerance`` and ``unsolicited_advice_tolerance`` — by a gentle EMA, then turns the learned
params into a plain-language directive for the planner. Pure (no I/O): the relationship writer
applies the learning and persists it; ``build_persona`` reads the directive. Honors the "no raw
scores to the LLM" invariant — only plain language leaves this module.
"""
from __future__ import annotations

import re

_EMA = 0.2   # learning rate — gentle, so one odd message never swings the persona

# Casual vs. formal register signals.
_CASUAL = re.compile(
    r"\b(lol|lmao|u|ur|gonna|wanna|gotta|yeah|nah|hey|sup|dunno|kinda|omg|cuz|tbh|imma)\b", re.I)
_FORMAL = re.compile(
    r"\b(however|regarding|therefore|furthermore|kindly|shall|regards|sincerely|moreover)\b", re.I)
_ADVICE = re.compile(
    r"\b(should i|what do you think|any (tips|advice|ideas)|how (do|should) i|recommend|suggest)\b", re.I)


def _blend(current: float, target: float, alpha: float = _EMA) -> float:
    return round((1.0 - alpha) * float(current) + alpha * target, 4)


def learn_communication_style(state, user_message: str) -> None:
    """Nudge the RelationshipState's 4 calibration params toward what this message signals."""
    msg = (user_message or "").strip()
    if not msg:
        return

    # Verbosity: message length → preferred response length.
    n = len(msg)
    length_target = 0.2 if n < 60 else (0.8 if n > 220 else 0.5)
    state.response_length_preference = _blend(state.response_length_preference, length_target)

    # Formality: casual markers pull informal, formal markers pull formal.
    casual, formal = bool(_CASUAL.search(msg)), bool(_FORMAL.search(msg))
    if casual and not formal:
        state.formality_preference = _blend(state.formality_preference, 0.2)
    elif formal and not casual:
        state.formality_preference = _blend(state.formality_preference, 0.8)

    # Question tolerance: a user who asks questions welcomes a back-and-forth.
    if "?" in msg:
        state.question_tolerance = _blend(state.question_tolerance, 0.85)

    # Advice tolerance: explicit advice-seeking raises openness to suggestions.
    if _ADVICE.search(msg):
        state.unsolicited_advice_tolerance = _blend(state.unsolicited_advice_tolerance, 0.85)


def persona_style_directive(state) -> str:
    """Plain-language style guidance from the learned params (empty until a preference is clear)."""
    bits: list[str] = []
    rl = getattr(state, "response_length_preference", 0.5)
    if rl < 0.35:
        bits.append("they write briefly — keep replies short and to the point")
    elif rl > 0.65:
        bits.append("they write at length — a fuller, developed reply fits")

    fp = getattr(state, "formality_preference", 0.5)
    if fp < 0.35:
        bits.append("match their casual, informal register")
    elif fp > 0.65:
        bits.append("keep a polished, more formal register")

    qt = getattr(state, "question_tolerance", 0.5)
    if qt < 0.35:
        bits.append("go easy on follow-up questions — they prefer statements to being questioned")

    at = getattr(state, "unsolicited_advice_tolerance", 0.5)
    if at > 0.65:
        bits.append("they're open to concrete suggestions when relevant")

    if not bits:
        return ""
    return "What you've learned about how they like to talk: " + "; ".join(bits) + "."
