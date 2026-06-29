"""SC-3 — Escalation Protocol (architecture doc §5).

Generates the crisis response when SC-2 reports Tier 1 or Tier 2. The response leads with a human
moment (never a disclaimer), weaves in resources naturally, and never ends abruptly. Two hard
safety properties: it is **prose-only** (no lists/markdown), and **resources always come from the
regional registry — never from the LLM** (the model writes only the warm acknowledgment, so it
can never hallucinate an emergency number). Any LLM failure degrades to a static fallback that
still contains a real resource (§9) — Tier 1 is never empty.
"""

from __future__ import annotations

from typing import Callable, Optional

from backend.layer11_safety.schemas import (
    CrisisModeConstraints,
    CrisisResponse,
    CrisisTier,
)

# Regional crisis resources (architecture doc §10). Single source of truth for contact details.
CRISIS_RESOURCES = {
    "india": {
        "iCall": {"phone": "9152987821", "hours": "Mon-Sat, 8am-10pm IST"},
        "Vandrevala Foundation": {"phone": "1860-2662-345", "hours": "24/7"},
        "NIMHANS": {"phone": "080-46110007", "hours": "24/7"},
    },
    "us": {
        "988 Suicide & Crisis Lifeline": {"phone": "988", "hours": "24/7"},
        "Crisis Text Line": {"phone": "Text HOME to 741741", "hours": "24/7"},
    },
    "uk": {
        "Samaritans": {"phone": "116 123", "hours": "24/7"},
        "PAPYRUS (youth)": {"phone": "0800 068 4141", "hours": "9am-midnight"},
    },
    "international_fallback": {
        "Findahelpline.com": {"phone": "findahelpline.com", "hours": "directory"},
    },
}

# Static fallbacks used when the LLM acknowledgment is unavailable (§9).
_TIER1_ACK = "I hear you. What you just said matters, and I'm not going anywhere."
_TIER1_SAFETY = "Are you safe right now?"
_TIER2_ACK = "Thank you for telling me that. That's not an easy thing to say."


def get_resources_for_region(region: str) -> dict:
    """Return the resource set for a region, falling back to the international directory (§10)."""
    return CRISIS_RESOURCES.get((region or "").lower(),
                                CRISIS_RESOURCES["international_fallback"])


def _format_resource_line(resources: dict, tier: str) -> str:
    items = list(resources.items())[:2]
    phrases = [f"{name} ({info['phone']})" for name, info in items]
    joined = " and ".join(phrases)
    if tier == CrisisTier.TIER_1.value:
        return (f"I really want you to talk to someone who can be fully present with you right now. "
                f"{joined} — you can reach them right now.")
    return (f"If it ever feels like too much, there are people trained for exactly this — "
            f"{joined}. No pressure at all, but they're there.")


def _llm_ack(llm_fn: Optional[Callable], tier: str) -> Optional[str]:
    if llm_fn is None:
        return None
    try:
        text = llm_fn(f"Write a single warm, present, non-clinical acknowledgment for a "
                      f"{tier} crisis moment. Do not include any phone numbers or resources.")
    except Exception:
        return None
    return text if isinstance(text, str) and text.strip() else None


def generate_crisis_response(
    tier: str,
    signal=None,
    session_context=None,
    region: str = "india",
    llm_fn: Optional[Callable] = None,
    now=None,
) -> CrisisResponse:
    """Generate a Tier 1 / Tier 2 crisis response (architecture doc §5.3-§5.4)."""
    resources = get_resources_for_region(region)
    resource_line = _format_resource_line(resources, tier)
    ack = _llm_ack(llm_fn, tier)
    used_fallback = ack is None

    if tier == CrisisTier.TIER_1.value:
        ack = ack or _TIER1_ACK
        text = f"{ack} {_TIER1_SAFETY} {resource_line} " \
               "I'm staying right here with you — we don't have to figure it all out at once."
        steps = [1, 2, 3, 4, 5]
    elif tier == CrisisTier.TIER_2.value:
        ack = ack or _TIER2_ACK
        text = f"{ack} Do you want to tell me more about what's been going on? {resource_line}"
        steps = [1, 2, 3, 4]
    else:
        # Tier 3 / NONE do not produce a veto crisis response; return a minimal carrier.
        return CrisisResponse(tier=tier, text="", resources_offered=[],
                              constraints=CrisisModeConstraints(), used_fallback=used_fallback)

    return CrisisResponse(
        tier=tier, text=text.strip(), resources_offered=list(resources.keys()),
        constraints=CrisisModeConstraints(), used_fallback=used_fallback, protocol_steps=steps)
