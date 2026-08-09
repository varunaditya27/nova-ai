"""SC-4 · Identity memory — update threshold, belief update, and contradiction detection
(architecture doc §6.3, §6.4).

Identity Memory is Nova's self-model. Beliefs resist change in proportion to their centrality;
immutable safety policies never change. Contradicting evidence must accumulate across sessions
past the centrality-scaled threshold before a belief is rewritten.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, Optional
from uuid import UUID

from .schemas import BeliefUpdateEvent, IdentityContradiction, IdentityEvidence, IdentityMemory

# A belief-statement generator: (belief, contradiction) → new statement. Production wires an
# LLM here; the default is a deterministic placeholder so the pipeline runs offline.
BeliefGenerator = Callable[[IdentityMemory, IdentityContradiction], str]

# Below this, a single call's contradiction_score is treated as noise, not evidence — protects
# accumulated evidence_against from drifting upward on marginal/uncertain LLM signal.
_CONTRADICTION_FLOOR = 0.15


def _default_generator(belief: IdentityMemory, contradiction: IdentityContradiction) -> str:
    return f"[revised] {belief.statement}"


def update_threshold(centrality: float) -> float:
    """threshold(centrality) = 0.5 × (1 + centrality²). Scales resistance with centrality (§6.3)."""
    return 0.5 * (1.0 + centrality * centrality)


def apply_identity_update(
    belief: IdentityMemory,
    contradiction: IdentityContradiction,
    prior_against_strength: Optional[float] = None,
    now: datetime | None = None,
    generate_fn: BeliefGenerator = _default_generator,
) -> bool:
    """Update an identity belief if accumulated contradictory evidence crosses threshold (§6.4).

    Immutable beliefs never update. ``prior_against_strength`` defaults to the sum of
    ``belief.evidence_against``'s own strengths (now that it's structured, see
    ``IdentityEvidence``) — pass an explicit value only to override that. Returns ``True`` if the
    belief was rewritten.

    If ``generate_fn`` returns an empty string or the belief's current statement unchanged (its
    best-effort failure/degradation contract — see ``api/state.py``'s real generator), that is
    treated as "couldn't rewrite this turn," not as a rewrite to identical text: the evidence is
    still recorded (so a later successful rewrite can pick up where this one left off) but no
    ``BeliefUpdateEvent`` is logged and the belief is left untouched. Without this, a caller whose
    generation call fails would otherwise get ``_default_generator``'s literal
    ``"[revised] <statement>"`` placeholder persisted as if it were real — production must always
    inject a real ``generate_fn``; the default exists only so this module runs standalone/offline.
    """
    if belief.is_immutable:
        return False

    now = now or datetime.utcnow()
    if prior_against_strength is None:
        prior_against_strength = sum(e.strength for e in belief.evidence_against)
    total_evidence = prior_against_strength + contradiction.strength
    threshold = belief.update_threshold or update_threshold(belief.centrality)
    evidence_entry = IdentityEvidence(
        summary=contradiction.evidence_summary, strength=contradiction.strength,
        session_id=contradiction.session_id, recorded_at=now,
    )

    if total_evidence < threshold:
        belief.evidence_against.append(evidence_entry)
        return False

    new_statement = generate_fn(belief, contradiction)
    if not new_statement or new_statement == belief.statement:
        belief.evidence_against.append(evidence_entry)
        return False

    belief.update_history.append(
        BeliefUpdateEvent(
            updated_at=now,
            prior_statement=belief.statement,
            new_statement=new_statement,
            triggering_session_id=contradiction.session_id,
            evidence_strength=contradiction.strength,
            update_reason=contradiction.evidence_summary,
        )
    )
    belief.statement = new_statement
    belief.last_updated = now
    belief.evidence_against = []   # spent — the new statement starts with a clean slate
    return True


def detect_identity_contradictions(
    client, message: str, beliefs: list[IdentityMemory], session_id: UUID,
) -> list[IdentityContradiction]:
    """SC-4 contradiction detection (§6.4): one combined LLM call over every non-immutable belief.

    Deliberately not per-belief and not embedding-pre-filtered: this is a single-user app with a
    small belief set (dozens, not hundreds), so one call giving the LLM the full belief list is
    both cheaper and more accurate than a cheap similarity pre-filter that risks discarding a real
    contradiction phrased in unrelated-looking words (see docs/layer-2-architecture.md §24).
    Best-effort: any failure yields no contradictions, never blocks the turn.
    """
    candidates = [b for b in beliefs if not b.is_immutable]
    if client is None or not message or not candidates:
        return []

    listing = "\n".join(f"- [{b.belief_id}] {b.statement}" for b in candidates)
    prompt = (
        "Nova is an AI companion with the self-beliefs listed below. Read the user's message and "
        "decide whether it gives Nova genuine reason to reconsider any of them -- e.g. the user "
        "explicitly disagrees with a stated opinion, asks for something that conflicts with a "
        "stated policy or trait, or reacts in a way that contradicts it. Return ONLY a JSON list "
        "of objects: {\"belief_id\": <exact id in brackets below>, \"contradiction_score\": 0-1, "
        "\"reason\": short string}. Only include a belief if there's a genuine, clear "
        "contradiction -- omit anything uncertain, unrelated, or where the message merely doesn't "
        "come up. If nothing contradicts, return [].\n\nBeliefs:\n" + listing +
        "\n\nUser message:\n" + message[:2000]
    )
    try:
        from infra.llm.json_extract import extract_json
        data = json.loads(extract_json(client.complete(prompt)))
        if not isinstance(data, list):
            return []
    except Exception:
        return []

    by_id = {str(b.belief_id): b for b in candidates}
    out: list[IdentityContradiction] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        belief = by_id.get(str(entry.get("belief_id", "")))
        if belief is None:
            continue
        try:
            score = float(entry.get("contradiction_score", 0.0))
        except (TypeError, ValueError):
            continue
        if score < _CONTRADICTION_FLOOR:
            continue
        out.append(IdentityContradiction(
            belief_id=belief.belief_id, evidence_summary=str(entry.get("reason", ""))[:500],
            contradiction_score=score, session_id=session_id, strength=score,
        ))
    return out
