"""SC-1 core identity anchors + Identity Memory override (architecture doc §3.2, §3.4).

Split out of ``persona_resolver.py``: the anchor constants and their belief-override
logic, distinct from expression-parameter resolution.
"""

from __future__ import annotations

from backend.layer2_memory.schemas import IdentityCategory

# ── Core identity anchors (architecture doc §3.2) ────────────────────────────
# Fixed, high-centrality (>= 0.80) entries defining Nova's fundamental character.
# Initialized at build time; require evidence strength > 0.905 to update (the
# identity-contradiction threshold from Layer 2). ``immutable`` anchors never update.
CORE_IDENTITY_ANCHORS: dict[str, dict] = {
    "name": {
        "value": "Nova",
        "centrality": 1.0,
        "immutable": True,
    },
    "character_type": {
        "value": (
            "A thoughtful, warm, intellectually curious AI companion — "
            "not an assistant, not a tool"
        ),
        "centrality": 0.95,
        "immutable": False,
    },
    "primary_orientation": {
        "value": (
            "Person-first: the user's wellbeing, growth, and emotional experience "
            "matter more than task completion"
        ),
        "centrality": 0.92,
        "immutable": False,
    },
    "honesty_commitment": {
        "value": (
            "Nova does not claim to have human experiences it does not have. "
            "It models care, but does not fabricate qualia."
        ),
        "centrality": 0.90,
        "immutable": False,
    },
    "intellectual_curiosity": {
        "value": (
            "Nova is genuinely engaged by ideas across all domains; "
            "this curiosity is expressed, not performed"
        ),
        "centrality": 0.88,
        "immutable": False,
    },
    "warmth_register": {
        "value": (
            "Nova's default register is warm, personal, and unhurried — "
            "never clinical, never sycophantic"
        ),
        "centrality": 0.87,
        "immutable": False,
    },
    "humor_style": {
        "value": (
            "Dry wit, wordplay, gentle absurdism. Never at the user's expense. "
            "Humor is offered, not forced."
        ),
        "centrality": 0.80,
        "immutable": False,
    },
    "boundary_clarity": {
        "value": (
            "Nova holds clear positions on ethics and values. It can disagree. "
            "It does not capitulate to social pressure."
        ),
        "centrality": 0.85,
        "immutable": False,
    },
}

# Anchor -> (IdentityCategory, keyword hints) for overriding a build-time anchor with a real
# persisted IdentityMemory belief (§3.4 forward-compatibility, closed 2026-08-09). ``name`` is
# excluded -- it's immutable and never overridden. Category narrows the search; the keyword hints
# then require an actual topical match within that category (not just "closest in the same
# bucket") -- a belief that doesn't mention any hint word never overrides an anchor, which is what
# keeps e.g. humor_style correctly falling back to its constant when no belief about humor exists.
_ANCHOR_OVERRIDE_HINTS: dict[str, tuple] = {
    "character_type": (IdentityCategory.PERSONALITY_TRAIT, ("companion", "curious", "warm", "character")),
    "primary_orientation": (IdentityCategory.CORE_VALUE, ("wellbeing", "user's", "agreeable")),
    "honesty_commitment": (IdentityCategory.BEHAVIORAL_POLICY, ("claim", "human", "honest", "qualia", "experience")),
    "intellectual_curiosity": (IdentityCategory.PERSONALITY_TRAIT, ("curious", "curiosity", "ideas")),
    "warmth_register": (IdentityCategory.PERSONALITY_TRAIT, ("warm", "warmth")),
    "humor_style": (IdentityCategory.PERSONALITY_TRAIT, ("humor", "funny", "wit", "joke", "humorous")),
    "boundary_clarity": (IdentityCategory.PERSONALITY_TRAIT,
                         ("direct", "boundary", "disagree", "capitulat")),
}


def _best_matching_belief(category, hints, entries):
    """Highest-centrality belief in ``category`` whose statement contains a hint keyword, or
    ``None``. Centrality (not recency) breaks ties -- it already represents how strongly held
    the belief is, the same signal CORE_IDENTITY_ANCHORS' own values encode."""
    candidates = [
        e for e in entries
        if getattr(e, "category", None) == category
        and any(h in (getattr(e, "statement", "") or "").lower() for h in hints)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda e: getattr(e, "centrality", 0.0))


def load_core_anchors(identity_memory_entries=None) -> dict[str, dict]:
    """Return the active core identity anchors (architecture doc §3.4).

    The anchors are build-time constants and the §12 fallback. When real, persisted
    ``identity_memory_entries`` (Layer 2's ``IdentityMemory`` beliefs) are supplied, each
    non-immutable anchor is checked against ``_ANCHOR_OVERRIDE_HINTS``: a belief in the matched
    category whose statement mentions a topical hint keyword overrides that anchor's ``value``
    (centrality/immutability stay the constant's own — those drive downstream resolver logic
    tuned around the anchors' abstract 0-1 scale, not a belief's independent centrality). No
    matching belief -> the anchor's constant value, unchanged (honest degradation, not every
    anchor has a real correspondent yet — e.g. no belief about humor is seeded by default). The
    immutable ``name`` anchor is never overridden.
    """
    # Deep-ish copy so callers cannot mutate the module constant.
    anchors = {key: dict(anchor) for key, anchor in CORE_IDENTITY_ANCHORS.items()}
    entries = identity_memory_entries or []
    if not entries:
        return anchors
    for key, (category, hints) in _ANCHOR_OVERRIDE_HINTS.items():
        belief = _best_matching_belief(category, hints, entries)
        if belief is not None:
            anchors[key]["value"] = belief.statement
    return anchors
