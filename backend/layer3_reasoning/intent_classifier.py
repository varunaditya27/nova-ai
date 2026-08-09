"""SC-3 — Intent Classifier (architecture doc §5).

Rule-first, LLM-fallback. A small regex table resolves the unambiguous ~60% of messages
with zero latency; the rest fall through to the shared SC-1/SC-3 LLM call (injected as
``llm_fn``). The ``prefers_no_advice`` flag is a *hard* constraint (§5.4) computed
independently of the path and OR-ed over any LLM opinion, so an unloading user is never
handed unsolicited solutions.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from backend.layer3_reasoning.schemas import (
    ClassificationMethod,
    IntentClassification,
    IntentLabel,
    LLMClassificationOutput,
    TopicDomain,
)

LLMFn = Callable[[str], LLMClassificationOutput]

# (pattern, label_or_None, confidence). A None label means "matched but not decidable by
# rule alone — defer to the LLM" (architecture doc §5.3).
INTENT_RULES: list[tuple[str, Optional[str], float]] = [
    (r"(just need to vent|just want to vent|not looking for advice|just want to talk)",
     IntentLabel.VENTING.value, 0.95),
    (r"^(what|where|when|who|how|why|which)\s.+\?$",
     IntentLabel.SEEKING_INFORMATION.value, 0.85),
    (r"^(can|could) you\s(help|tell|show|suggest|recommend)",
     IntentLabel.SEEKING_ADVICE.value, 0.80),
    (r"(wanted to let you know|turns out|by the way|btw|^update\b)",
     IntentLabel.PROVIDING_UPDATE.value, 0.75),
    (r"(i don.t know|i'm confused|im confused|what do i do|i can.t decide)",
     None, 0.0),  # ambiguous; LLM required
]

# Intents that imply advice/validation needs on the rule path.
_ADVICE_INTENTS = {
    IntentLabel.SEEKING_ADVICE.value, IntentLabel.PROBLEM_SOLVING.value,
    IntentLabel.DECISION_SUPPORT.value, IntentLabel.GOAL_SETTING.value,
}
_VALIDATION_INTENTS = {
    IntentLabel.SEEKING_VALIDATION.value, IntentLabel.SEEKING_COMFORT.value,
    IntentLabel.VENTING.value,
}

# Phrases that explicitly decline advice (architecture doc §5.4).
NO_ADVICE_PHRASES = [
    "don't give me advice", "dont give me advice", "no advice",
    "not looking for solutions", "not looking for advice",
    "just need to vent", "just want to vent", "just want to talk",
]

RULE_CONFIDENCE_FLOOR = 0.70
LONG_VALIDATION_WORDS = 150
ADVICE_FRUSTRATION_THRESHOLD = 2


def rule_classify(message: str) -> Optional[tuple[str, float]]:
    """Return (label, confidence) for a confident rule match, else ``None`` (§5.3)."""
    lowered = message.lower()
    for pattern, label, confidence in INTENT_RULES:
        if re.search(pattern, lowered):
            if label is not None and confidence > RULE_CONFIDENCE_FLOOR:
                return label, confidence
            return None  # matched an explicitly-ambiguous rule → defer to LLM
    return None


def compute_prefers_no_advice(
    message: str,
    primary_intent: str,
    advice_frustration_count: int = 0,
) -> bool:
    """Hard constraint: should Nova withhold solutions entirely? (architecture doc §5.4)."""
    lowered = message.lower()

    if any(p in lowered for p in NO_ADVICE_PHRASES):
        return True
    if primary_intent == IntentLabel.VENTING.value and "?" not in message:
        return True
    if (primary_intent == IntentLabel.SEEKING_VALIDATION.value
            and len(message.split()) > LONG_VALIDATION_WORDS):
        return True
    if advice_frustration_count > ADVICE_FRUSTRATION_THRESHOLD:
        return True
    return False


def classify_intent(
    message: str,
    *,
    llm_fn: Optional[LLMFn] = None,
    llm_output: Optional[LLMClassificationOutput] = None,
    advice_frustration_count: int = 0,
) -> IntentClassification:
    """Full SC-3 path: rule → (use | LLM fallback), with prefers_no_advice overlaid (§5).

    ``llm_output`` lets a caller pass an already-fetched shared SC-1/SC-3 result (architecture
    doc §14.2) instead of this function calling ``llm_fn`` itself — see
    ``emotion_classifier.classify_emotion`` for the matching parameter and
    ``build_emotion_intent_packet`` for the single shared call site. When ``llm_output`` is
    given, ``llm_fn`` is never invoked.
    """
    rule = rule_classify(message)

    if rule is not None:
        label, confidence = rule
        intent = IntentClassification(
            primary_intent=label,
            intent_confidence=confidence,
            needs_advice=label in _ADVICE_INTENTS,
            needs_validation=label in _VALIDATION_INTENTS,
            topic_domain=TopicDomain.OTHER.value,
            classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
        )
    elif llm_output is not None or llm_fn is not None:
        out = llm_output if llm_output is not None else llm_fn(message)
        intent = IntentClassification(
            primary_intent=out.primary_intent,
            secondary_intent=out.secondary_intent,
            intent_confidence=out.intent_confidence,
            needs_advice=out.needs_advice,
            needs_validation=out.needs_validation,
            prefers_no_advice=out.prefers_no_advice,
            topic_domain=out.topic_domain,
            classification_method=ClassificationMethod.LLM_ONLY.value,
        )
    else:
        # Degraded: no rule match and no LLM → safe casual default (architecture doc §12).
        intent = IntentClassification(
            primary_intent=IntentLabel.CASUAL_CHAT.value,
            intent_confidence=0.4,
            classification_method=ClassificationMethod.HEURISTIC_ONLY.value,
        )

    # §5.4 is a hard constraint — overlay it on top of whatever the path produced.
    intent.prefers_no_advice = intent.prefers_no_advice or compute_prefers_no_advice(
        message, intent.primary_intent, advice_frustration_count)
    return intent
