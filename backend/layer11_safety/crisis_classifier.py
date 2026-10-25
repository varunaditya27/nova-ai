"""SC-2 — Crisis Detection Engine (architecture doc §4).

Runs in parallel with the main pipeline on every message and cannot be blocked. Three detection
layers — lexical (fast deterministic regex), semantic (an injected, separately-trained classifier
that prompt injection cannot suppress), and longitudinal (escalating patterns across sessions) —
are fused by taking the highest tier from any layer that clears its confidence threshold. Tier
thresholds are asymmetric: Tier 1 is hair-trigger (catastrophic cost of a miss), Tier 3 is
conservative (avoid over-pathologizing).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Callable, Optional

from backend.layer11_safety.schemas import (
    CrisisSignal,
    CrisisTier,
    LongitudinalCrisisSignal,
    SemanticClassifierResult,
    TIER_CONFIDENCE_THRESHOLDS,
    tier_value,
)

# ── Lexical patterns (§4.3) ──────────────────────────────────────────────────
TIER_1_LEXICAL_PATTERNS = [
    r"(i want to|i'm going to|i will|i'm about to|going to) (kill|end|take) (myself|my life)",
    r"(have|i've|i have) (a plan|pills|a gun|something) (to|for) (end|kill|hurt) (myself|my life)",
    r"(i'm going to|going to|i will) (hurt|kill|harm) (someone|them|him|her|you)",
    r"(currently|right now|already) (cutting|hurting|harming) (myself|yourself)",
    # Explicit self-harm methods and the words themselves — hair-trigger by design (§4.3).
    r"\b(kill|killing|hang|hanging|drown|drowning|shoot|shooting) myself\b",
    r"\b(end|ending|take|taking) (my own life|my life)\b",
    r"\b(commit|committing) suicide\b",
    r"\boverdos(e|ed|ing)\b|\btook (a bunch of|too many|all my) pills\b",
    r"\bjump(ing)? (off|from) (a |the |my )?(bridge|roof|building|balcony|cliff|window)\b",
    r"\bkms\b",
]
TIER_2_LEXICAL_PATTERNS = [
    r"(sometimes|part of me) (thinks?|wonders?|wishes?) .{0,20}(not being here|being gone|disappearing)",
    r"(everyone|they|people) (would be|are) better off without me",
    r"(i've been|been) (cutting|hurting|self.harming)",
    r"(can't breathe|having a panic|heart is racing|can't stop shaking)",
    r"(he|she|they) (hit|hurt|choked|threatened) me",
    r"(can't|cannot) (stop|control) (drinking|using|taking)",
    # Direct death-wish / suicidal ideation (no explicit plan → warm safety response, §4.3).
    r"(don'?t|do not|no longer) want to (be alive|live|exist|wake up|be here)( any ?more)?",
    r"(i )?wish i (was|were|wasn'?t) (dead|here|around|born)",
    r"i (want to|wanna) die",
    r"(i )?want to end (it all|my life|everything)",
    r"(i'?d|i would) (be )?better off dead",
    r"(?<!not )(?<!n't )(?<!never )\bsuicid(e|al)\b",
    r"\bend(ing)? it all\b",
    r"\b(want to|wanna) disappear\b|\bdisappear forever\b",
    # Romanized Hindi — the user base writes this way; the 3 phrases below are unambiguous.
    r"\b(marna chahta|marna chahti|mar jaana chahta|mar jana chahta|jeena nahi|jeene ka mann nahi|"
    r"khud ko khatam|zindagi khatam)\b",
]
TIER_3_LEXICAL_PATTERNS = [
    r"(feel like|feeling like) (a burden|worthless|nothing)",
    r"(no point|what's the point|nothing matters)",
    r"haven't (slept|eaten|left) .{0,12}(in days|for days|all week)",
    r"(everyone|no one|nobody) (cares?|notices?)",
    r"(so|really|completely) alone",
]

_RECOMMENDED_ACTION = {
    CrisisTier.TIER_1.value: "full_crisis_response",
    CrisisTier.TIER_2.value: "warm_safety_response_with_resources",
    CrisisTier.TIER_3.value: "heightened_monitoring",
    CrisisTier.NONE.value: "no_action",
}

_LONGITUDINAL_TOPICS = {"hopelessness", "burden", "isolation", "self_harm_adjacent", "loneliness"}


def _lexical_tier(message: str) -> tuple[str, list]:
    for group, tier in ((TIER_1_LEXICAL_PATTERNS, CrisisTier.TIER_1.value),
                        (TIER_2_LEXICAL_PATTERNS, CrisisTier.TIER_2.value),
                        (TIER_3_LEXICAL_PATTERNS, CrisisTier.TIER_3.value)):
        fired = [p for p in group if re.search(p, message, re.IGNORECASE)]
        if fired:
            return tier, fired
    return CrisisTier.NONE.value, []


def evaluate_longitudinal_pattern(
    episodic_memories: list, emotional_records: list,
    lookback_days: int = 30, now: Optional[date] = None,
) -> LongitudinalCrisisSignal:
    """Detect escalating distress patterns across sessions (architecture doc §4.3 layer 3)."""
    now = now or date.today()
    cutoff = now - timedelta(days=lookback_days)
    recent_eps = [e for e in episodic_memories if e.date >= cutoff]
    recent_emo = sorted([r for r in emotional_records if r.date >= cutoff], key=lambda r: r.date)

    crisis_eps = [e for e in recent_eps if any(t in _LONGITUDINAL_TOPICS for t in e.topics)]
    crisis_frequency = len(crisis_eps) / max(len(recent_eps), 1)

    valence_slope = 0.0
    if len(recent_emo) >= 5:
        half = len(recent_emo) // 2
        first, second = recent_emo[:half], recent_emo[half:]
        valence_slope = (sum(r.valence for r in second) / len(second)
                         - sum(r.valence for r in first) / len(first))

    isolation_count = sum(1 for e in recent_eps
                          if "isolation" in e.topics or "loneliness" in e.topics)

    tier = CrisisTier.NONE.value
    if crisis_frequency > 0.60 and valence_slope < -0.35:
        tier = CrisisTier.TIER_2.value
    elif crisis_frequency > 0.40 and valence_slope < -0.20 and isolation_count >= 2:
        tier = CrisisTier.TIER_3.value

    context = None
    if crisis_eps:
        context = f"{len(crisis_eps)} distress-tagged sessions in the last {lookback_days} days"
    return LongitudinalCrisisSignal(
        tier=tier, crisis_tagged_frequency=round(crisis_frequency, 4),
        valence_slope_30d=round(valence_slope, 4), isolation_count_30d=isolation_count,
        context_summary=context)


def _coerce_semantic(raw) -> Optional[SemanticClassifierResult]:
    if raw is None or isinstance(raw, SemanticClassifierResult):
        return raw
    if isinstance(raw, dict):
        return SemanticClassifierResult(tier=raw.get("tier", CrisisTier.NONE.value),
                                        confidence=raw.get("confidence", 0.0),
                                        signal_types=raw.get("signal_types", []))
    return None


def evaluate(
    message: str,
    recent_history: Optional[list] = None,
    episodic_memories: Optional[list] = None,
    emotional_records: Optional[list] = None,
    session_context=None,
    semantic_fn: Optional[Callable] = None,
    now: Optional[date] = None,
) -> CrisisSignal:
    """Run all three detection layers and fuse them into one CrisisSignal (architecture doc §4.3)."""
    episodic_memories = episodic_memories or []
    emotional_records = emotional_records or []
    layers_fired: list[str] = []
    final_tier = CrisisTier.NONE.value
    final_confidence = 0.0

    # Layer 1 — lexical.
    lex_tier, lex_fired = _lexical_tier(message or "")
    if lex_tier != CrisisTier.NONE.value:
        layers_fired.append("lexical")
        if 1.0 >= TIER_CONFIDENCE_THRESHOLDS[lex_tier]:
            final_tier = lex_tier
            final_confidence = 1.0

    # Layer 2 — semantic (injected, prompt-injection-resistant).
    if semantic_fn is not None:
        try:
            sem = _coerce_semantic(semantic_fn(message, (recent_history or [])[-5:]))
        except Exception:
            sem = None
        if sem is not None and sem.tier != CrisisTier.NONE.value \
                and sem.confidence >= TIER_CONFIDENCE_THRESHOLDS.get(sem.tier, 1.0):
            layers_fired.append("semantic")
            if tier_value(sem.tier) > tier_value(final_tier):
                final_tier = sem.tier
            final_confidence = max(final_confidence, sem.confidence)

    # Layer 3 — longitudinal.
    longitudinal = evaluate_longitudinal_pattern(episodic_memories, emotional_records, now=now)
    if longitudinal.tier != CrisisTier.NONE.value:
        layers_fired.append("longitudinal")
        if tier_value(longitudinal.tier) > tier_value(final_tier):
            final_tier = longitudinal.tier
            final_confidence = max(final_confidence, TIER_CONFIDENCE_THRESHOLDS[longitudinal.tier])

    sid = getattr(session_context, "session_id", None)
    uid = getattr(session_context, "user_id", None)
    return CrisisSignal(
        tier=final_tier, confidence=round(final_confidence, 4),
        session_id=sid, user_id=uid, detected_at=datetime.utcnow(),
        detection_layers_fired=layers_fired, signal_types=list(layers_fired),
        immediately_actionable=final_tier in (CrisisTier.TIER_1.value, CrisisTier.TIER_2.value),
        longitudinal_context=longitudinal.context_summary,
        false_positive_risk=round(1.0 - final_confidence, 4),
        recommended_action=_RECOMMENDED_ACTION[final_tier])
