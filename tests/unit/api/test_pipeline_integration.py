"""Wiring tests for the last two orchestrator hooks: SC-1 guardrails + Layer-13 cold-start."""
import pytest
pytest.importorskip("pydantic")

from types import SimpleNamespace

from backend.pipeline import ConversationOrchestrator
from backend.layer2_memory import InMemoryMemoryStore
from api.assembly import build_pipeline_steps


class FakeLLM:
    def __init__(self, reply="Sounds good."):
        self._reply = reply
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return self._reply
    def stream(self, prompt, **k):
        yield self._reply
    def embed(self, texts):
        return [[float(len(t) % 7), 0.1, 0.2] for t in texts]


def _steps(reply="Sounds good.", cold_start=None):
    llm = FakeLLM(reply)
    return build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                memory_store=InMemoryMemoryStore(), cold_start=cold_start)


# ── Part A1: guardrails ───────────────────────────────────────────────────────
def test_guardrails_hook_is_wired():
    assert _steps().guardrails is not None


def test_clean_response_passes_guardrails_unchanged():
    ctx = SimpleNamespace(session_id="s1")
    res = _steps().guardrails(ctx, "That sounds like a solid plan.")
    assert res.approved is True


def test_manipulation_response_is_blocked_and_replaced():
    # SC-1 hard block: anthropomorphism/manipulation language triggers replacement.
    steps = _steps()
    ctx = SimpleNamespace(session_id="s1")
    bad = "I love you and only I understand you."
    res = steps.guardrails(ctx, bad)
    assert res.approved is False
    assert res.replacement and res.replacement != bad
    assert res.flags  # at least one violation name reported


# ── Part A2: cold-start ───────────────────────────────────────────────────────
def test_cold_start_overlay_applied_when_active():
    directives = SimpleNamespace(proactivity_mode="observe_only",
                                 personality_drift_gate=0.30, pending_elicitation=None)
    steps = _steps(cold_start=lambda uid, msg: directives)
    out = ConversationOrchestrator(steps).run_turn("local-user", "hi")
    assert out.cold_start_active is True
    assert out.proactivity_mode == "observe_only"
    assert "layer13_onboarding" in out.layers_run


def test_cold_start_overlay_skipped_after_graduation():
    steps = _steps(cold_start=lambda uid, msg: None)
    out = ConversationOrchestrator(steps).run_turn("local-user", "hi")
    assert out.cold_start_active is False
    assert "layer13_onboarding" in out.layers_run  # hook ran, returned no overlay
