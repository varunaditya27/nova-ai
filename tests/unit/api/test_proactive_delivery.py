"""Tests for api/proactive_delivery.py -- Layer-6 SC-4 message generation + SC-3 gating, shared
between GET /proactive and background/proactive_check_job.py (architecture doc §5, §6).

Uses the real ``build_app_state`` (not a stub steps object) so ``build_proactive_context`` runs
against the actual ``build_persona`` closure -- this is the exact seam a live-only bug slipped
through on 2026-08-09 (``build_persona`` reads ``ctx.input_packet``/``ctx.emotion_intent``
directly, not getattr-safe on ``ctx`` itself; a bare ``SimpleNamespace`` without them raised
``AttributeError``, silently caught by ``build_persona``'s own try/except and degrading
``voice_parameters`` to defaults). A test double for ``steps`` would never have caught this.
"""
import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from datetime import datetime, timedelta, timezone

from infra.db import make_engine, make_session_factory, init_db
from infra.db.proactive_store import PostgresProactiveQueue
from infra.db.relationship_store import PostgresRelationshipStore
from backend.layer6_proactivity.schemas import ProactiveItem
from api.proactive_delivery import build_proactive_context, gate_passes, generate_message_for_item
from api.state import build_app_state

_SAFE_NOW = datetime(2026, 8, 9, 14, 0, tzinfo=timezone.utc)   # afternoon band, no gate races


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "Hey! Been thinking about how your study routine is going -- hope it's treating you well."
    def stream(self, prompt, **k):
        yield "hi there"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _sqlite_state():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    return build_app_state(config={"system": {"default_user_id": "local-user"},
                                   "llm": {}, "memory": {}},
                           llm_clients=clients, engine=engine, vector_store=object())


def _developing_relationship(state):
    rel = PostgresRelationshipStore(state.session_factory, "local-user")
    for i in range(20):
        rel.record_turn(f"s{i}")


def test_build_proactive_context_against_the_real_build_persona():
    """Regression for the live-only AttributeError: build_proactive_context's ctx must carry a
    real input_packet.circadian_band and emotion_intent.background_state, or build_persona's
    voice-calibration step silently degrades to defaults."""
    state = _sqlite_state()
    _developing_relationship(state)
    item = ProactiveItem(item_id="p1", item_type="goal_check_in",
                         content_basis="a real, detailed reason to check in on your 5k goal")

    ctx = build_proactive_context(state, item, "local-user", _SAFE_NOW)

    assert "developing" in ctx.persona_instruction
    assert ctx.voice_parameters_summary          # non-empty -- proves calibrate_voice ran for real
    assert ctx.relationship_stage == "developing"


def test_generate_message_for_item_produces_real_text_for_a_gate_passing_item():
    state = _sqlite_state()
    _developing_relationship(state)
    item = ProactiveItem(item_id="p1", item_type="goal_check_in",
                         content_basis="a real, detailed reason to check in on your 5k goal")

    text = generate_message_for_item(state, item, "local-user", _SAFE_NOW)

    assert text and "study routine" in text


def test_generate_message_for_item_returns_none_without_an_llm_client():
    state = _sqlite_state()
    state.llm_clients = {}
    item = ProactiveItem(item_id="p1", item_type="goal_check_in", content_basis="x" * 30)
    assert generate_message_for_item(state, item, "local-user", _SAFE_NOW) is None


def test_gate_passes_blocks_a_brand_new_relationship():
    from api.proactive_delivery import build_timing_context

    state = _sqlite_state()
    item = ProactiveItem(item_id="p1", item_type="goal_check_in",
                         content_basis="a real, detailed reason to check in on your 5k goal")
    now = _SAFE_NOW
    ctx = build_timing_context(state.session_factory, "local-user", now, state.config)
    assert gate_passes(item, ctx, now) is False


def test_gate_passes_allows_a_clearable_item():
    from api.proactive_delivery import build_timing_context

    state = _sqlite_state()
    _developing_relationship(state)
    item = ProactiveItem(item_id="p1", item_type="goal_check_in",
                         content_basis="a real, detailed reason to check in on your 5k goal")
    now = _SAFE_NOW
    ctx = build_timing_context(state.session_factory, "local-user", now, state.config)
    assert gate_passes(item, ctx, now) is True
