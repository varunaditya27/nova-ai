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


def test_evidence_against_accumulates_structured_strength_across_calls():
    """Without an explicit prior_against_strength, it's computed from belief.evidence_against's
    own stored strengths -- proving accumulation genuinely works turn to turn, not just when a
    caller manually threads a running total through (test_accumulated_evidence_eventually_updates
    _central_belief covers that explicit-override path)."""
    belief = _belief(centrality=0.9)  # threshold 0.905
    changed = identity.apply_identity_update(belief, _contradiction(belief, 0.5))
    assert changed is False
    assert len(belief.evidence_against) == 1
    assert belief.evidence_against[0].strength == 0.5

    changed = identity.apply_identity_update(belief, _contradiction(belief, 0.5))
    assert changed is True   # 0.5 (accumulated) + 0.5 (this call) = 1.0 >= 0.905
    assert belief.evidence_against == []   # spent -- fresh slate for the new statement


def test_evidence_against_resets_after_an_actual_update():
    belief = _belief(centrality=0.2)  # threshold 0.52
    identity.apply_identity_update(belief, _contradiction(belief, 0.7))
    assert belief.evidence_against == []
    assert len(belief.update_history) == 1


class _StubLLM:
    def __init__(self, response):
        self._response = response
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return self._response


def test_detect_identity_contradictions_matches_flagged_belief_by_id():
    belief = _belief(centrality=0.5)
    llm = _StubLLM(
        f'[{{"belief_id": "{belief.belief_id}", "contradiction_score": 0.8, '
        f'"reason": "user asked for a long, detailed answer"}}]')
    out = identity.detect_identity_contradictions(
        llm, "give me every detail, don't summarize", [belief], session_id=uuid4())
    assert len(out) == 1
    assert out[0].belief_id == belief.belief_id
    assert out[0].strength == 0.8


def test_detect_identity_contradictions_excludes_immutable_beliefs_from_the_prompt():
    immutable = _belief(centrality=1.0, immutable=True)
    calls = []

    class RecordingLLM:
        def complete(self, prompt, **k):
            calls.append(prompt)
            return "[]"

    identity.detect_identity_contradictions(RecordingLLM(), "hello", [immutable], session_id=uuid4())
    assert calls == []   # no candidates -> no LLM call at all


def test_detect_identity_contradictions_drops_scores_below_the_noise_floor():
    belief = _belief(centrality=0.5)
    llm = _StubLLM(f'[{{"belief_id": "{belief.belief_id}", "contradiction_score": 0.05, '
                   f'"reason": "very weak signal"}}]')
    out = identity.detect_identity_contradictions(
        llm, "hmm maybe", [belief], session_id=uuid4())
    assert out == []


def test_detect_identity_contradictions_degrades_to_empty_on_malformed_response():
    belief = _belief(centrality=0.5)
    llm = _StubLLM("not json at all")
    out = identity.detect_identity_contradictions(
        llm, "whatever", [belief], session_id=uuid4())
    assert out == []
