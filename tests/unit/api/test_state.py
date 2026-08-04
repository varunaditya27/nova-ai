import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from datetime import datetime, timezone

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail
from backend.layer2_memory.schemas import EpisodicMemory, ScoredMemory
from api.state import build_app_state, make_state_update_writer, make_cold_start_provider


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "hi there"
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


class Ctx:
    user_id = "local-user"
    session_id = "s1"
    message = "hey there"
    now = datetime.now(timezone.utc)
    response_text = "loves hiking"
    emotion_intent = None
    recalled_memories = []


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_writer_persists_episode_session_and_audit():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1)(Ctx())
    assert any(m.summary == "hey there" for m in store.active_episodic("local-user"))
    with session_scope(factory) as s:
        assert s.query(models.Session).filter_by(session_key="s1").one().turn_count == 1
    assert PostgresAuditTrail(factory, "local-user").verify() is True


def test_writer_reinforces_similarity_matched_recalled_memory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="loves hiking",
                         embedding=[0.1, 0.2, 0.3], S_current=0.5,
                         created_at=datetime.now(timezone.utc))
    store.save_episodic(mem)

    class C(Ctx):
        recalled_memories = [ScoredMemory(memory=mem, effective_score=0.9)]
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1)(C())
    assert store.get_episodic(mem.memory_id).S_current > 0.5


def test_goal_writer_persists_extracted_goal():
    from infra.db.goal_store import PostgresGoalStore
    from api.state import make_goal_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class GoalLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return '{"goal_detected": true, "new_goal": {"inferred_title": "run a 5k", "confidence": 0.8}}'

    class GoalCtx(Ctx):
        message = "I want to run a 5k next month"

    make_goal_writer(factory, GoalLLM(), FakeLLM())(GoalCtx())
    active = PostgresGoalStore(factory, "local-user").load_by_status(["active"])
    assert any(g.title == "run a 5k" for g in active)


def test_safety_writer_records_crisis_and_skips_none():
    from types import SimpleNamespace
    from infra.db.safety_store import PostgresSafetyLog
    from backend.layer11_safety.schemas import CrisisSignal
    from api.state import make_safety_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    writer = make_safety_writer(factory)

    def _ctx(tier):
        sig = CrisisSignal(tier=tier)
        return SimpleNamespace(user_id="local-user", session_id="s1",
                               crisis_assessment=SimpleNamespace(signal=sig))

    writer(_ctx("none"))
    assert PostgresSafetyLog(factory).recent("local-user") == []
    writer(_ctx("tier_2"))
    recent = PostgresSafetyLog(factory).recent("local-user")
    assert len(recent) == 1 and recent[0].tier == "tier_2" and recent[0].user_id == "local-user"


def test_onboarding_writer_counts_and_graduates():
    from types import SimpleNamespace
    from infra.db.onboarding_store import PostgresOnboardingStore
    from api.state import make_onboarding_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    writer = make_onboarding_writer(factory, graduation_sessions=2)
    writer(SimpleNamespace(user_id="local-user", session_id="s1"))
    assert PostgresOnboardingStore(factory, "local-user").state()["cold_start_active"] is True
    writer(SimpleNamespace(user_id="local-user", session_id="s2"))
    st = PostgresOnboardingStore(factory, "local-user").state()
    assert st["session_index"] == 2 and st["cold_start_active"] is False


def test_cold_start_provider_active_then_graduated():
    from infra.db.onboarding_store import PostgresOnboardingStore
    from api.state import make_onboarding_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    provider = make_cold_start_provider(factory, graduation_sessions=1)
    # No record yet → still cold-starting → directives with observe-only overlay.
    d = provider("local-user", "hi")
    assert d is not None and d.proactivity_mode == "observe_only" and d.personality_drift_gate == 0.30
    # Advance past graduation → provider returns None (overlay self-terminates).
    make_onboarding_writer(factory, graduation_sessions=1)(
        __import__("types").SimpleNamespace(user_id="local-user", session_id="s1"))
    assert PostgresOnboardingStore(factory, "local-user").state()["cold_start_active"] is False
    assert provider("local-user", "hi") is None


def test_temporal_profile_provider_derives_from_relationship_and_message_stores():
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.message_store import PostgresMessageStore
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    rel = PostgresRelationshipStore(factory, "local-user")
    rel.record_turn("s1")
    rel.record_turn("s2")
    rel.record_turn("s3")

    msgs = PostgresMessageStore(factory, "local-user")
    msgs.append("user", "hi", session_key="s1",
                created_at=datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc))   # evening
    msgs.append("user", "still going strong", session_key="s2",
                created_at=datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc))  # evening, +4 days
    msgs.append("user", "one more", session_key="s3",
                created_at=datetime(2026, 1, 9, 20, 0, tzinfo=timezone.utc))  # evening, +4 days

    provider = make_temporal_profile_provider(factory)
    d = provider("local-user")

    assert d["total_sessions"] == 3
    assert d["relationship_age_days"] == pytest.approx(
        (datetime.now(timezone.utc) - datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)).days, abs=1)
    assert d["last_session_end"] == datetime(2026, 1, 9, 20, 0, tzinfo=timezone.utc)
    # Mean GAP BETWEEN sessions (s1->s2 and s2->s3 are both 4 days apart) — NOT
    # relationship_age_days / total_sessions, which would give a much smaller, wrong number
    # and silently defeat detect_temporal_anomaly's cadence check (see api/state.py comment).
    assert d["average_session_frequency_days"] == pytest.approx(4.0)
    # Below the minimum-sample floor (3 banded messages < 10) — stays empty rather than reporting
    # a low-confidence histogram that would flag every unseen band as "atypical".
    assert d["typical_bands"] == {}
    assert d["message_length_median_chars"] is not None


def test_temporal_profile_provider_populates_bands_above_sample_floor():
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.message_store import PostgresMessageStore
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    rel = PostgresRelationshipStore(factory, "local-user")
    msgs = PostgresMessageStore(factory, "local-user")
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(9):   # 9 evening messages
        rel.record_turn(f"s{i}")
        msgs.append("user", "evening chat", session_key=f"s{i}",
                    created_at=base.replace(day=1 + i, hour=20))
    rel.record_turn("s9")
    msgs.append("user", "morning chat", session_key="s9", created_at=base.replace(day=10, hour=9))

    d = make_temporal_profile_provider(factory)("local-user")
    assert d["typical_bands"]["evening"] == pytest.approx(0.9)
    assert d["typical_bands"]["morning"] == pytest.approx(0.1)


def test_temporal_profile_provider_applies_timezone_offset_to_band_histogram():
    """The historical band histogram must apply the same timezone_offset_hours as the live
    circadian band computed in api/assembly.py::perceive, or the two silently diverge
    (docs/layer-1-architecture.md §16, 'Circadian histogram is UTC-based')."""
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.message_store import PostgresMessageStore
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    rel = PostgresRelationshipStore(factory, "local-user")
    msgs = PostgresMessageStore(factory, "local-user")
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # 20:00 UTC == 01:30 IST (+5:30) the next day — "evening" in UTC, "late_night" in IST.
    for i in range(10):
        rel.record_turn(f"s{i}")
        msgs.append("user", "message", session_key=f"s{i}", created_at=base.replace(day=1 + i, hour=20))

    utc_bands = make_temporal_profile_provider(factory)("local-user")["typical_bands"]
    ist_bands = make_temporal_profile_provider(factory, 5.5)("local-user")["typical_bands"]

    assert utc_bands == {"evening": pytest.approx(1.0)}
    assert ist_bands == {"late_night": pytest.approx(1.0)}


def test_temporal_profile_provider_empty_history_yields_no_bands():
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    d = make_temporal_profile_provider(factory)("brand-new-user")
    assert d["total_sessions"] == 0
    assert d["relationship_age_days"] == 0
    assert d["typical_bands"] == {}
    assert d["last_session_end"] is None
    assert d["message_length_median_chars"] is None
