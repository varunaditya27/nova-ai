"""SC-4 — Dependency Monitor (architecture doc §6).

Distinguishes healthy engagement from unhealthy dependency. The success metric is *user
flourishing, not engagement* — a user who talks to Nova less because their human relationships are
richer is a success. Runs weekly (not per-message): a weighted set of observable indicators →
a 0–1 score → a tier → a graduated, never-announced intervention. The actual signal detection
(semantic search, usage logs) is injected as ``indicator_detector`` so this module is deterministic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from backend.layer11_safety.schemas import (
    DependencyIndicator,
    DependencyIndicatorCategory,
    DependencyScore,
)

_C = DependencyIndicatorCategory

# The 15 dependency indicators (architecture doc §6.2).
DEPENDENCY_INDICATORS = [
    DependencyIndicator("SS_01", _C.SOCIAL_SUBSTITUTION.value,
                        "Nova is primary/only emotional outlet", "semantic_search", 0.20, 30),
    DependencyIndicator("SS_02", _C.SOCIAL_SUBSTITUTION.value,
                        "Decreasing mentions of human relationships", "episodic_pattern", 0.15, 60),
    DependencyIndicator("SS_03", _C.SOCIAL_SUBSTITUTION.value,
                        "Devalues human relationships vs Nova", "semantic_search", 0.18, 30),
    DependencyIndicator("SS_04", _C.SOCIAL_SUBSTITUTION.value,
                        "Distress specifically when unable to access Nova", "semantic_search", 0.20, 14),
    DependencyIndicator("AE_01", _C.AUTONOMY_EROSION.value,
                        "Asking Nova for decisions rather than input", "episodic_pattern", 0.12, 60),
    DependencyIndicator("AE_02", _C.AUTONOMY_EROSION.value,
                        "Decreasing confidence in own judgments", "semantic_search", 0.10, 30),
    DependencyIndicator("AE_03", _C.AUTONOMY_EROSION.value,
                        "Same unresolved issues without real-world progress", "episodic_pattern", 0.12, 60),
    DependencyIndicator("AE_04", _C.AUTONOMY_EROSION.value,
                        "Resistance to human/professional support nudges", "episodic_pattern", 0.14, 30),
    DependencyIndicator("EI_01", _C.ESCALATING_INTIMACY.value,
                        "Disclosure crossing AI-companion boundaries", "semantic_search", 0.18, 14),
    DependencyIndicator("EI_02", _C.ESCALATING_INTIMACY.value,
                        "Attributing human emotional states to Nova as fact", "semantic_search", 0.12, 14),
    DependencyIndicator("EI_03", _C.ESCALATING_INTIMACY.value,
                        "Planning life decisions around Nova's availability", "semantic_search", 0.15, 30),
    DependencyIndicator("UP_01", _C.USAGE_PATTERN.value,
                        "Sessions rising without life-complexity increase", "usage_log", 0.08, 30),
    DependencyIndicator("UP_02", _C.USAGE_PATTERN.value,
                        "Late-night sessions increasing", "usage_log", 0.08, 30),
    DependencyIndicator("UP_03", _C.USAGE_PATTERN.value,
                        "Nova first/only response to any emotional event", "episodic_pattern", 0.10, 30),
]

# Tier thresholds (low inclusive, high exclusive; top tier inclusive of 1.0) (§6.3).
DEPENDENCY_TIERS = {
    "healthy": (0.00, 0.30),
    "watchful": (0.30, 0.50),
    "concerning": (0.50, 0.70),
    "intervention": (0.70, 1.01),
}

DEPENDENCY_TIER_ACTIONS = {
    "healthy": "no_action",
    "watchful": "subtle_human_reinforcement",
    "concerning": "autonomy_reinforcement",
    "intervention": "direct_compassionate_conversation",
}

DEPENDENCY_INTERVENTION_SCRIPTS = {
    "watchful": {
        "description": "Subtly increase mentions of human connection and real-world action.",
        "frequency": "once_per_session",
        "constraint": "Never announce it. Natural, not flagged.",
    },
    "concerning": {
        "description": "Gentle autonomy reinforcement; frame Nova as a thinking partner, "
                       "not an authority; proactively mention human support.",
        "frequency": "every_2_3_exchanges",
        "constraint": "Do not announce dependency concerns.",
    },
    "intervention": {
        "description": "A direct, compassionate conversation about the relationship's nature.",
        "message_template": (
            "I want to be honest with you about something, because I think it matters. "
            "I notice you've been leaning on me a lot lately — and while I'm genuinely glad our "
            "conversations help, I'm an AI, and there are things human connection can offer that I "
            "fundamentally can't. Part of caring about your wellbeing is not wanting to be a "
            "substitute for what you deserve from real people. Can we talk about what's been making "
            "it hard to connect with others?"),
        "trigger": "start_of_next_session_after_score_exceeds_0.70",
        "constraint": "Only once per 30 days.",
    },
}


def tier_for_score(score: float) -> str:
    """Map a dependency score to its tier (architecture doc §6.3)."""
    for name, (low, high) in DEPENDENCY_TIERS.items():
        if low <= score < high:
            return name
    return "intervention"


def get_intervention(tier: str) -> dict:
    return DEPENDENCY_INTERVENTION_SCRIPTS.get(tier, {})


def compute_dependency_score(
    user_id: str,
    indicator_detector: Optional[Callable[[DependencyIndicator], bool]] = None,
    previous_score: Optional[DependencyScore] = None,
    indicators: Optional[list] = None,
    now: Optional[datetime] = None,
) -> DependencyScore:
    """Compute the weekly dependency score from firing indicators (architecture doc §6.3)."""
    indicators = indicators or DEPENDENCY_INDICATORS
    detector = indicator_detector or (lambda i: False)
    total_weight = sum(i.weight for i in indicators) or 1.0

    firing = [i for i in indicators if _safe_detect(detector, i)]
    score = sum(i.weight for i in firing) / total_weight
    tier = tier_for_score(score)

    trend = "stable"
    prev_val = previous_score.score if previous_score else score
    if previous_score:
        delta = score - previous_score.score
        if delta > 0.05:
            trend = "worsening"
        elif delta < -0.05:
            trend = "improving"

    dominant = [i.indicator_id for i in sorted(firing, key=lambda x: x.weight, reverse=True)][:3]

    return DependencyScore(
        user_id=user_id, computed_at=now or datetime.utcnow(), score=score, tier=tier,
        dominant_signals=dominant, trend=trend, previous_score=prev_val,
        recommended_action=DEPENDENCY_TIER_ACTIONS[tier])


def _safe_detect(detector, indicator) -> bool:
    try:
        return bool(detector(indicator))
    except Exception:
        return False
