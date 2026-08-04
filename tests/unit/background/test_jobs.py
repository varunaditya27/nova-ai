import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timezone
from types import SimpleNamespace

from infra.db.engine import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.proactive_store import PostgresProactiveQueue
from infra.db.longitudinal_store import PostgresLongitudinalStore
from backend.layer2_memory.schemas import EmotionVector, EpisodicMemory
from backend.layer6_proactivity.schemas import ProactiveItem
from background import scheduler


def _state(user="u1"):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    return SimpleNamespace(session_factory=factory, default_user_id=user,
                           config={"onboarding": {"graduation_sessions": 5}})


def _add_episode(factory, uid, summary="hi", strength=0.5, valence=0.0, arousal=0.0):
    PostgresMemoryStore(factory).save_episodic(EpisodicMemory(
        user_id=uid, summary=summary, embedding=[0.1, 0.2], S_current=strength,
        importance_score=0.2, emotion_vector=EmotionVector(valence=valence, arousal=arousal),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))


def test_integrity_job_reports_intact():
    out = scheduler.run_job(_state(), "integrity_check")
    assert out["status"] == "INTACT"


def test_consolidation_job_decays_and_persists():
    st = _state()
    _add_episode(st.session_factory, "u1", strength=0.5)
    out = scheduler.run_job(st, "memory_consolidation")
    assert out["swept"] == 1
    # A very old, weak episode should have decayed strength persisted.
    ep = PostgresMemoryStore(st.session_factory).all_episodic("u1")[0]
    assert ep.last_decay_computed_at is not None


def test_consolidation_job_runs_semantic_extraction_when_triggered():
    st = _state()
    now = datetime.now(timezone.utc)
    # 55 (>= EPISODE_COUNT_TRIGGER=50) near-identical, fresh (undecayed as of "now") episodes
    # so a cluster forms and none of them get swept away by the decay pass first.
    store = PostgresMemoryStore(st.session_factory)
    for i in range(55):
        store.save_episodic(EpisodicMemory(
            user_id="u1", summary=f"felt anxious about work #{i}",
            embedding=[1.0, 0.0, 0.0], S_current=1.0, importance_score=0.8,
            created_at=now, last_decay_computed_at=now))

    from background.memory_consolidation_job import run
    result = run(st)

    assert result["clusters_detected"] >= 1
    assert result["semantic_memories_created"] >= 1
    assert len(store.active_semantic("u1")) >= 1


def test_proactive_job_maintains_queue_when_graduated():
    st = _state()
    # graduate so proactivity is not suppressed
    from infra.db.onboarding_store import PostgresOnboardingStore
    ob = PostgresOnboardingStore(st.session_factory, "u1", graduation_sessions=1)
    ob.record_turn("s1")
    q = PostgresProactiveQueue(st.session_factory, "u1")
    q.upsert(ProactiveItem(item_id="p1", item_type="goal_check_in", status="pending"))
    out = scheduler.run_job(st, "proactive_check")
    assert out.get("queued") == 1


def test_proactive_job_skips_during_cold_start():
    st = _state()
    out = scheduler.run_job(st, "proactive_check")  # no onboarding record → cold_start_active
    assert out.get("skipped") == "cold_start_active"


def test_longitudinal_job_generates_and_persists_summary():
    st = _state()
    _add_episode(st.session_factory, "u1")
    with session_scope(st.session_factory) as s:
        s.add(models.Session(user_id="u1", session_key="s1", turn_count=3))
    out = scheduler.run_job(st, "longitudinal_summary")
    assert out["summary_id"]
    assert PostgresLongitudinalStore(st.session_factory, "u1").latest() is not None


def test_pattern_job_runs():
    st = _state()
    _add_episode(st.session_factory, "u1")
    out = scheduler.run_job(st, "pattern_detection")
    assert "patterns" in out and out["episodes"] == 1


def test_episodic_records_reads_real_emotion_vector_not_content_basis_valence():
    """_adapters.episodic_records used to read a field, `content_basis_valence`, that doesn't
    exist on EpisodicMemory (that name belongs to Layer 6's ProactiveItem) -- emotional_intensity
    was always 0.0 regardless of the episode's real emotion. The real field is emotion_vector."""
    from infra.db.memory_store import PostgresMemoryStore
    from background._adapters import episodic_records

    st = _state()
    _add_episode(st.session_factory, "u1", valence=-0.8, arousal=0.6)
    recs = episodic_records(PostgresMemoryStore(st.session_factory), "u1")
    assert len(recs) == 1
    assert recs[0].emotional_intensity == pytest.approx(0.8)


def test_emotional_records_adapter_derives_records_from_episode_emotion_vectors():
    from infra.db.memory_store import PostgresMemoryStore
    from background._adapters import emotional_records

    st = _state()
    _add_episode(st.session_factory, "u1", valence=-0.5, arousal=0.4)
    recs = emotional_records(PostgresMemoryStore(st.session_factory), "u1")
    assert len(recs) == 1
    assert recs[0].valence == pytest.approx(-0.5)
    assert recs[0].arousal == pytest.approx(0.4)


def test_longitudinal_job_populates_emotional_summary_from_real_episodes():
    """generate_weekly_summary previously always received emotional_records=[] -- the weekly
    summary's emotional texture was always empty regardless of real session emotion."""
    st = _state()
    now = datetime.now(timezone.utc)
    PostgresMemoryStore(st.session_factory).save_episodic(EpisodicMemory(
        user_id="u1", summary="a rough day", embedding=[0.1, 0.2], S_current=0.5,
        importance_score=0.2, emotion_vector=EmotionVector(valence=-0.6, arousal=0.5),
        created_at=now))
    with session_scope(st.session_factory) as s:
        s.add(models.Session(user_id="u1", session_key="s1", turn_count=3))

    out = scheduler.run_job(st, "longitudinal_summary")
    summary = PostgresLongitudinalStore(st.session_factory, "u1").latest()
    assert summary is not None
    assert summary.emotional_summary.avg_valence != 0.0


def test_start_scheduler_noop_when_disabled():
    st = _state()  # scheduler.enabled defaults absent/false
    assert scheduler.start_scheduler(st) is None


def test_dependency_monitor_job_computes_score_from_episodic_keywords():
    st = _state()
    _add_episode(st.session_factory, "u1",
                summary="I told Nova she's the only one who really understands me, "
                        "better than my friends")

    from background.dependency_monitor_job import run
    result = run(st)

    assert "tier" in result
    assert "score" in result
    assert 0.0 <= result["score"] <= 1.0


def test_dependency_monitor_job_zero_score_with_no_signals():
    st = _state()
    _add_episode(st.session_factory, "u1", summary="had a great day at the park with friends")
    result = scheduler.run_job(st, "dependency_monitor")
    assert result["score"] == 0.0
    assert result["tier"] == "healthy"


def test_job_registry_has_six_jobs():
    assert len(scheduler.JOBS) == 6
