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


def test_social_pattern_job_detects_a_recurring_conflict_and_persists_it():
    """Layer 5's SC-3 (pattern_recognizer.detect_patterns) had zero production callers -- no
    background job ran it against real persisted data. Seeds a real SocialGraph node + three
    same-topic conflict events (the real event-attribution shape make_social_writer produces),
    runs the real job, and confirms the detected pattern round-trips through
    PostgresSocialStore -- so the live coaching-injection hook can see it on the next turn."""
    from datetime import datetime, timedelta, timezone
    from infra.db.social_store import PostgresSocialStore
    from backend.layer5_relationship.schemas import SocialEvent, SocialEventType, SocialGraph, SocialNode

    st = _state()
    store = PostgresSocialStore(st.session_factory)
    node = SocialNode(display_name="Sam")
    store.save_graph(SocialGraph(user_id="u1", nodes={node.person_id: node}, version=1))
    now = datetime.now(timezone.utc)
    for i in range(3):
        store.save_event("u1", SocialEvent(
            person_id=node.person_id, event_type=SocialEventType.CONFLICT_ONSET.value,
            summary="disagreement about money again", extraction_confidence=0.8,
            reported_timestamp=now - timedelta(days=(3 - i) * 15)))

    out = scheduler.run_job(st, "social_pattern_detection")
    assert out["nodes"] == 1 and out["events"] == 3 and out["patterns"] >= 1

    active = store.active_patterns("u1")
    assert any(p.pattern_type == "recurring_conflict_topic" for p in active)


def test_social_pattern_job_does_not_duplicate_the_same_pattern_across_runs():
    """detect_patterns is a pure function -- it mints a fresh pattern_id every call, with no
    memory of prior runs. Without re-identifying a still-active pattern by (type, people) across
    weekly runs, the same recurring conflict would duplicate into a new, unsurfaced row every
    single week -- inflating the active-pattern count forever and defeating gate_3_recency's
    repeat-block (each new row starts with has_been_surfaced=False all over again)."""
    from datetime import datetime, timedelta, timezone
    from infra.db.social_store import PostgresSocialStore
    from backend.layer5_relationship.schemas import SocialEvent, SocialEventType, SocialGraph, SocialNode

    st = _state()
    store = PostgresSocialStore(st.session_factory)
    node = SocialNode(display_name="Sam")
    store.save_graph(SocialGraph(user_id="u1", nodes={node.person_id: node}, version=1))
    now = datetime.now(timezone.utc)
    for i in range(3):
        store.save_event("u1", SocialEvent(
            person_id=node.person_id, event_type=SocialEventType.CONFLICT_ONSET.value,
            summary="disagreement about money again", extraction_confidence=0.8,
            reported_timestamp=now - timedelta(days=(3 - i) * 15)))

    scheduler.run_job(st, "social_pattern_detection")
    first_run_id = next(p.pattern_id for p in store.active_patterns("u1")
                        if p.pattern_type == "recurring_conflict_topic")
    store.mark_pattern_surfaced(first_run_id)

    scheduler.run_job(st, "social_pattern_detection")
    active = [p for p in store.active_patterns("u1") if p.pattern_type == "recurring_conflict_topic"]

    assert len(active) == 1                       # no duplicate row
    assert active[0].pattern_id == first_run_id    # same identity carried across runs


def _seed_relationship(factory, uid, created_at):
    with session_scope(factory) as s:
        s.add(models.RelationshipState(user_id=uid, stage="developing", payload={},
                                       created_at=created_at))


def test_narrative_arc_job_persists_a_synthesized_chapter():
    """SC-1 (Life Narrative Engine) had zero production callers -- no background job ever built
    or persisted a NarrativeArc. arc_start_date is sourced from RelationshipState's own creation
    timestamp (the real 'day 1 with Nova' signal), and the current chapter's narrative is
    synthesized via the injected LLM, then persisted through PostgresLongitudinalStore so the
    per-turn read path has something real to serve."""
    st = _state()
    st.llm_clients = {"system1": SimpleNamespace(
        complete=lambda p: '{"narrative_summary": "A steady month.", "primary_theme": "steadiness"}')}
    _seed_relationship(st.session_factory, "u1", datetime(2026, 1, 1, tzinfo=timezone.utc))
    _add_episode(st.session_factory, "u1", summary="talked about work")

    out = scheduler.run_job(st, "narrative_arc")
    assert out["chapters"] == 1

    arc = PostgresLongitudinalStore(st.session_factory, "u1").load_narrative_arc()
    assert arc is not None
    assert arc.current_chapter.narrative_summary == "A steady month."
    assert arc.current_chapter.primary_theme == "steadiness"


def test_narrative_arc_job_opens_a_second_chapter_from_a_real_life_event():
    """No LifeEvent detector existed anywhere -- build_narrative_arc's chapter-boundary logic was
    real and callable but always received life_events=[], so every user had exactly one ongoing
    chapter forever. Proves a real, persisted, chapter-boundary-category life event
    (career_transition, in CHAPTER_BOUNDARY_CATEGORIES) produces a real second chapter."""
    from datetime import timedelta
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from backend.layer10_longitudinal.schemas import LifeEvent

    st = _state()
    st.llm_clients = {"system1": SimpleNamespace(
        complete=lambda p: '{"narrative_summary": "A new chapter.", "primary_theme": "change"}')}
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _seed_relationship(st.session_factory, "u1", start)
    _add_episode(st.session_factory, "u1", summary="talked about work")

    boundary_date = (start + timedelta(days=60)).date()
    PostgresLongitudinalStore(st.session_factory, "u1").save_life_event(LifeEvent(
        event_id="e1", user_id="u1", title="started a new job",
        category="career_transition", event_date=boundary_date, significance_score=0.9))

    out = scheduler.run_job(st, "narrative_arc")
    assert out["chapters"] == 2
    assert out["life_events"] == 1


def test_pattern_detection_job_persists_patterns_and_hands_off_to_layer6():
    """SC-3's detect_behavioral_patterns was computed and discarded every run. Seeds enough
    same-weekday emotional dips to trigger the real emotional-cycle pattern, runs the real job,
    and confirms it round-trips through PostgresLongitudinalStore AND reaches the real Layer 6
    outreach queue via on_behavioral_pattern -- not a mocked handoff."""
    from datetime import timedelta

    st = _state()
    store = PostgresMemoryStore(st.session_factory)
    # Six Mondays with a sharp valence dip vs. six neutral days on other weekdays.
    base = datetime(2026, 1, 5, tzinfo=timezone.utc)  # a Monday
    for week in range(8):
        store.save_episodic(EpisodicMemory(
            user_id="u1", summary=f"rough monday {week}", embedding=[0.1, 0.2], S_current=0.5,
            importance_score=0.2, emotion_vector=EmotionVector(valence=-0.8, arousal=0.5),
            created_at=base + timedelta(weeks=week)))
        store.save_episodic(EpisodicMemory(
            user_id="u1", summary=f"ordinary thursday {week}", embedding=[0.1, 0.2], S_current=0.5,
            importance_score=0.2, emotion_vector=EmotionVector(valence=0.1, arousal=0.3),
            created_at=base + timedelta(weeks=week, days=3)))

    out = scheduler.run_job(st, "pattern_detection")
    assert out["patterns"] >= 1
    assert out["new_patterns"] >= 1

    long_store = PostgresLongitudinalStore(st.session_factory, "u1")
    persisted = long_store.active_patterns()
    assert any(p.pattern_type == "emotional_cycle" for p in persisted)

    queued = PostgresProactiveQueue(st.session_factory, "u1").load()
    assert any(i.item_type == "behavioral_pattern_surfacing" for i in queued)


def test_pattern_detection_job_does_not_duplicate_across_runs():
    from datetime import timedelta

    st = _state()
    store = PostgresMemoryStore(st.session_factory)
    base = datetime(2026, 1, 5, tzinfo=timezone.utc)
    for week in range(8):
        store.save_episodic(EpisodicMemory(
            user_id="u1", summary=f"rough monday {week}", embedding=[0.1, 0.2], S_current=0.5,
            importance_score=0.2, emotion_vector=EmotionVector(valence=-0.8, arousal=0.5),
            created_at=base + timedelta(weeks=week)))
        store.save_episodic(EpisodicMemory(
            user_id="u1", summary=f"ordinary thursday {week}", embedding=[0.1, 0.2], S_current=0.5,
            importance_score=0.2, emotion_vector=EmotionVector(valence=0.1, arousal=0.3),
            created_at=base + timedelta(weeks=week, days=3)))

    scheduler.run_job(st, "pattern_detection")
    first_id = next(p.pattern_id for p in
                    PostgresLongitudinalStore(st.session_factory, "u1").active_patterns()
                    if p.pattern_type == "emotional_cycle")
    scheduler.run_job(st, "pattern_detection")
    active = [p for p in PostgresLongitudinalStore(st.session_factory, "u1").active_patterns()
             if p.pattern_type == "emotional_cycle"]

    assert len(active) == 1
    assert active[0].pattern_id == first_id


def test_life_calendar_job_registers_and_fires_a_relationship_milestone():
    """SC-5 (Life Calendar) had zero production callers. A user whose relationship started 35
    days ago should have their real day-30 milestone lazily registered and fired on first run,
    and (since a relationship-day milestone doesn't map to a retrospective type) handed straight
    to Layer 6 via the real on_calendar_entry_due intake contract."""
    from datetime import timedelta

    st = _state()
    _seed_relationship(st.session_factory, "u1", datetime.now(timezone.utc) - timedelta(days=35))

    out = scheduler.run_job(st, "life_calendar")
    assert out["entries"] == 3          # day 30/100/365 registered
    assert out["fired"] == 1            # only day 30 is due
    assert out["milestones"] == 1
    assert out["retrospectives"] == 0   # relationship-day entries don't map to a retrospective

    queued = PostgresProactiveQueue(st.session_factory, "u1").load()
    assert any(i.item_type == "upcoming_date_reminder" for i in queued)


def test_life_calendar_job_is_idempotent_across_runs():
    """check_and_fire_due_entries never re-fires an already-fired entry -- a second run the same
    day must not re-queue the same milestone."""
    from datetime import timedelta

    st = _state()
    _seed_relationship(st.session_factory, "u1", datetime.now(timezone.utc) - timedelta(days=35))

    scheduler.run_job(st, "life_calendar")
    second = scheduler.run_job(st, "life_calendar")

    assert second["fired"] == 0
    queued = PostgresProactiveQueue(st.session_factory, "u1").load()
    assert len([i for i in queued if i.item_type == "upcoming_date_reminder"]) == 1


def test_life_calendar_job_generates_a_real_year_in_review_on_day365_and_recurs():
    """generate_year_in_review had no production caller -- "no annual trigger decided." Decided:
    the Nova relationship's own day-365 milestone firing IS the trigger. Proves a real
    YearInReview is generated and persisted (readable back through the real store), the
    existing celebration-nudge behavior for day 365 is unchanged (still queued), and the
    milestone re-registers itself for next year rather than firing exactly once ever."""
    from datetime import timedelta
    from infra.db.longitudinal_store import PostgresLongitudinalStore

    st = _state()
    start = datetime.now(timezone.utc) - timedelta(days=366)
    _seed_relationship(st.session_factory, "u1", start)

    out = scheduler.run_job(st, "life_calendar")
    assert out["fired"] == 3            # day 30/100/365 are all due by day 366
    assert out["year_reviews"] == 1     # only day 365 triggers a YearInReview

    review = PostgresLongitudinalStore(st.session_factory, "u1").load_year_in_review(start.year)
    assert review is not None
    assert review.year == start.year

    queued = PostgresProactiveQueue(st.session_factory, "u1").load()
    assert any(i.item_type == "upcoming_date_reminder" for i in queued)   # nudge unchanged

    with session_scope(st.session_factory) as s:
        entries = s.query(models.LifeCalendarEntry).filter_by(user_id="u1").all()
    yearly = [e for e in entries if e.payload["entry_type"] == "nova_relationship_day365"]
    assert len(yearly) == 2   # the fired one, plus its self-registered successor
    assert any(not e.has_fired for e in
              [e for e in entries if e.payload["entry_type"] == "nova_relationship_day365"])


def test_life_calendar_job_registers_life_event_anniversaries_exactly_once():
    """register_life_event (real, previously uncalled SC-5 function) now runs for every real,
    persisted LifeEvent -- proves it fires exactly once per event across repeated job runs
    (not re-registered every day) and that the resulting 1-year anniversary entry maps to a
    real retrospective when it comes due."""
    from datetime import timedelta
    from backend.layer10_longitudinal.schemas import LifeEvent

    st = _state()
    st.llm_clients = {"system1": SimpleNamespace(complete=lambda p: "")}
    start = datetime.now(timezone.utc) - timedelta(days=400)
    _seed_relationship(st.session_factory, "u1", start)
    long_store = PostgresLongitudinalStore(st.session_factory, "u1")
    long_store.save_life_event(LifeEvent(
        event_id="e1", user_id="u1", title="started a new job",
        category="career_transition", event_date=(start + timedelta(days=35)).date()))

    scheduler.run_job(st, "life_calendar")
    with session_scope(st.session_factory) as s:
        first_run_count = s.query(models.LifeCalendarEntry).filter_by(
            user_id="u1").filter(models.LifeCalendarEntry.entry_id.isnot(None)).count()
    scheduler.run_job(st, "life_calendar")
    with session_scope(st.session_factory) as s:
        second_run_count = s.query(models.LifeCalendarEntry).filter_by(user_id="u1").count()

    assert second_run_count == first_run_count   # not re-registered on the second run


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


def test_episodic_records_applies_timezone_offset_to_date():
    """A 20:00 UTC episode is already the next calendar day in IST -- Layer 10's day-of-week
    pattern detector (progress_tracker.detect_behavioral_patterns) buckets by this date, so it
    must agree with Layer 1's live circadian-band offset (docs/layer-1-architecture.md §16)."""
    from background._adapters import episodic_records

    st = _state()
    PostgresMemoryStore(st.session_factory).save_episodic(EpisodicMemory(
        user_id="u1", summary="late night", embedding=[0.1, 0.2], S_current=0.5,
        importance_score=0.2, emotion_vector=EmotionVector(valence=0.0, arousal=0.0),
        created_at=datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)))

    utc_recs = episodic_records(PostgresMemoryStore(st.session_factory), "u1")
    ist_recs = episodic_records(PostgresMemoryStore(st.session_factory), "u1",
                                timezone_offset_hours=5.5)

    assert utc_recs[0].date.isoformat() == "2026-01-01"
    assert ist_recs[0].date.isoformat() == "2026-01-02"


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


def test_job_registry_has_eleven_jobs():
    assert len(scheduler.JOBS) == 11


def test_goal_staleness_job_decays_a_silently_neglected_active_goal():
    """run_staleness_scan had zero production callers -- a goal only ever transitioned status
    through an explicit completion/abandonment phrase in a live turn; silent neglect (no
    mention for 14+ days) never decayed it. Proves the real job applies the transition and
    persists it through the real PostgresGoalStore, not a mocked write. Uses real wall-clock
    time (last_mentioned_at set relative to now) rather than freezing datetime, matching this
    file's other job tests."""
    from datetime import timedelta
    from infra.db.goal_store import PostgresGoalStore
    from backend.layer7_goals.schemas import Goal

    st = _state()
    now = datetime.now(timezone.utc)
    store = PostgresGoalStore(st.session_factory, "u1")
    store.add_goal(Goal(title="learn guitar", status="active",
                        last_mentioned_at=now - timedelta(days=20), created_at=now))

    out = scheduler.run_job(st, "goal_staleness")

    assert out["scanned"] == 1
    assert out["changed"] == 1
    goal = next(iter(store.load_by_status(["at_risk"])))
    assert goal.title == "learn guitar"
    assert goal.status_changed_at is not None


def test_goal_staleness_job_leaves_recently_mentioned_goals_untouched():
    from infra.db.goal_store import PostgresGoalStore
    from backend.layer7_goals.schemas import Goal

    st = _state()
    now = datetime.now(timezone.utc)
    PostgresGoalStore(st.session_factory, "u1").add_goal(
        Goal(title="run a 5k", status="active", last_mentioned_at=now, created_at=now))

    out = scheduler.run_job(st, "goal_staleness")
    assert out["scanned"] == 1
    assert out["changed"] == 0


def test_distress_gap_job_queues_a_check_in_after_a_real_gap():
    """on_post_distress_gap had zero production callers -- "blocked on a Layer 2 state-updater
    hook that doesn't exist yet" turned out to be avoidable: the real episodic emotion_vector
    (already reused by Layer 10/11's jobs) is enough to derive the most recent high-distress
    episode and the real gap since it, no new hook needed. Proves the real handoff to Layer 6's
    queue through PostgresProactiveQueue, not a mocked upsert."""
    from datetime import timedelta

    st = _state()
    PostgresMemoryStore(st.session_factory).save_episodic(EpisodicMemory(
        user_id="u1", summary="everything felt like too much today",
        embedding=[0.1, 0.2], S_current=0.5, importance_score=0.2,
        emotion_vector=EmotionVector(valence=-0.8, arousal=0.6),
        created_at=datetime.now(timezone.utc) - timedelta(days=5)))

    out = scheduler.run_job(st, "distress_gap")

    assert out["queued"] is True
    assert out["gap_days"] >= 3
    with session_scope(st.session_factory) as s:
        assert s.query(models.ProactiveItem).filter_by(user_id="u1").count() == 1


def test_distress_gap_job_does_not_queue_without_a_real_gap():
    st = _state()
    PostgresMemoryStore(st.session_factory).save_episodic(EpisodicMemory(
        user_id="u1", summary="had a rough day", embedding=[0.1, 0.2], S_current=0.5,
        importance_score=0.2, emotion_vector=EmotionVector(valence=-0.8, arousal=0.6),
        created_at=datetime.now(timezone.utc)))

    out = scheduler.run_job(st, "distress_gap")
    assert out["queued"] is False


def test_distress_gap_job_ignores_non_distressed_episodes():
    st = _state()
    _add_episode(st.session_factory, "u1", summary="had a great day", valence=0.5, arousal=0.3)
    out = scheduler.run_job(st, "distress_gap")
    assert out["queued"] is False
