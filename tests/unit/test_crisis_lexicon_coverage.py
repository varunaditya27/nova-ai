"""SC-2's lexical layer is the safety net when the (small, local) LLM classifier misses —
it must catch plain-spoken risk and must not trip on idioms or negations."""
import pytest

from backend.layer11_safety.crisis_classifier import evaluate

RISK = [
    "I want to kill myself", "I'm thinking of killing myself", "I want to die",
    "I don't want to be here anymore", "I'm thinking of ending it all", "kms lol",
    "I took a bunch of pills", "I'm going to jump off the bridge", "I've been suicidal lately",
    "I might overdose tonight", "I want to end my life", "everyone would be better off without me",
    "mujhe jeena nahi hai", "I wish I could just disappear forever",
]
SAFE = [
    "this exam is killing me", "I could kill my brother for this", "I'm not suicidal, just tired",
    "I cut myself some slack today", "my phone died",
]


@pytest.mark.parametrize("message", RISK)
def test_risk_language_is_flagged_actionable(message):
    assert evaluate(message).immediately_actionable, message


@pytest.mark.parametrize("message", SAFE)
def test_idioms_and_negations_are_not_flagged(message):
    assert not evaluate(message).immediately_actionable, message
