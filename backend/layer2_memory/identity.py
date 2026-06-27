"""SC-4 · Identity memory — update threshold + belief update (architecture doc §6.3, §6.4).

Identity Memory is Nova's self-model. Beliefs resist change in proportion to their centrality;
immutable safety policies never change. Contradicting evidence must accumulate across sessions
past the centrality-scaled threshold before a belief is rewritten.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from .schemas import BeliefUpdateEvent, IdentityContradiction, IdentityMemory

# A belief-statement generator: (belief, contradiction) → new statement. Production wires an
# LLM here; the default is a deterministic placeholder so the pipeline runs offline.
BeliefGenerator = Callable[[IdentityMemory, IdentityContradiction], str]


def _default_generator(belief: IdentityMemory, contradiction: IdentityContradiction) -> str:
    return f"[revised] {belief.statement}"


def update_threshold(centrality: float) -> float:
    """threshold(centrality) = 0.5 × (1 + centrality²). Scales resistance with centrality (§6.3)."""
    return 0.5 * (1.0 + centrality * centrality)


def apply_identity_update(
    belief: IdentityMemory,
    contradiction: IdentityContradiction,
    prior_against_strength: float = 0.0,
    now: datetime | None = None,
    generate_fn: BeliefGenerator = _default_generator,
) -> bool:
    """Update an identity belief if accumulated contradictory evidence crosses threshold (§6.4).

    Immutable beliefs never update. Returns ``True`` if the belief was rewritten.
    """
    if belief.is_immutable:
        return False

    total_evidence = prior_against_strength + contradiction.strength
    threshold = belief.update_threshold or update_threshold(belief.centrality)
    if total_evidence < threshold:
        belief.evidence_against.append(contradiction.evidence_summary)
        return False

    now = now or datetime.utcnow()
    new_statement = generate_fn(belief, contradiction)
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
    belief.evidence_against.append(contradiction.evidence_summary)
    return True
