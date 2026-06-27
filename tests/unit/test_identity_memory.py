"""Tests for SC-4 identity memory: update threshold + belief update (architecture doc §6.3, §6.4)."""

import math
from uuid import uuid4

from backend.layer2_memory import identity
from backend.layer2_memory.schemas import (
    IdentityCategory,
    IdentityContradiction,
    IdentityMemory,
)


def test_update_threshold_formula():
    # threshold(centrality) = 0.5 * (1 + centrality²)
    assert math.isclose(identity.update_threshold(0.2), 0.52, rel_tol=1e-9)
    assert math.isclose(identity.update_threshold(0.5), 0.625, rel_tol=1e-9)
    assert math.isclose(identity.update_threshold(0.9), 0.905, rel_tol=1e-9)
    assert identity.update_threshold(1.0) == 1.0


def _belief(centrality=0.2, immutable=False):
    return IdentityMemory(
        belief_id=uuid4(), category=IdentityCategory.OPINION,
        statement="Nova prefers concise answers", centrality=centrality,
        update_threshold=identity.update_threshold(centrality), is_immutable=immutable,
    )


def _contradiction(belief, strength):
    return IdentityContradiction(belief_id=belief.belief_id,
                                 evidence_summary="user wanted detailed answers",
                                 contradiction_score=strength, strength=strength)


def test_immutable_belief_never_updates():
    belief = _belief(centrality=0.2, immutable=True)
    changed = identity.apply_identity_update(belief, _contradiction(belief, 0.99))
    assert changed is False
    assert belief.statement == "Nova prefers concise answers"


def test_peripheral_belief_updates_with_strong_evidence():
    belief = _belief(centrality=0.2)  # threshold 0.52
    changed = identity.apply_identity_update(
        belief, _contradiction(belief, 0.7), prior_against_strength=0.0)
    assert changed is True
    assert len(belief.update_history) == 1
    assert belief.update_history[0].prior_statement == "Nova prefers concise answers"


def test_central_belief_resists_single_contradiction():
    belief = _belief(centrality=0.9)  # threshold 0.905
    changed = identity.apply_identity_update(belief, _contradiction(belief, 0.7))
    assert changed is False


def test_accumulated_evidence_eventually_updates_central_belief():
    belief = _belief(centrality=0.9)  # threshold 0.905
    changed = identity.apply_identity_update(
        belief, _contradiction(belief, 0.5), prior_against_strength=0.5)  # total 1.0 ≥ 0.905
    assert changed is True


def test_custom_generator_sets_statement():
    belief = _belief(centrality=0.2)
    identity.apply_identity_update(
        belief, _contradiction(belief, 0.9),
        generate_fn=lambda b, c: "Nova adapts answer length to the user",
    )
    assert belief.statement == "Nova adapts answer length to the user"
