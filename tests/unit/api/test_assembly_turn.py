import pytest
pytest.importorskip("pydantic")

from backend.pipeline import ConversationOrchestrator
from backend.layer2_memory import InMemoryMemoryStore
from api.assembly import build_pipeline_steps


class FakeLLM:
    """LLMClient-shaped fake: echoes a canned reply; deterministic, offline."""
    def __init__(self, reply="Sounds good - tell me more."):
        self._reply = reply
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return self._reply
    def stream(self, prompt, **k):
        yield self._reply
    def embed(self, texts):
        return [[float(len(t) % 7), 0.1, 0.2] for t in texts]


def _steps(session_writer=None):
    llm = FakeLLM()
    return build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                memory_store=InMemoryMemoryStore(),
                                session_writer=session_writer)


def test_casual_turn_runs_through_real_pipeline():
    out = ConversationOrchestrator(_steps()).run_turn("local-user", "hey what's up")
    assert isinstance(out.response_text, str) and out.response_text.strip()


def test_empty_recall_delivers_without_inventing_memories():
    out = ConversationOrchestrator(_steps()).run_turn("local-user", "hi")
    assert out.response_text.strip()


def test_state_writer_is_invoked_after_turn():
    seen = []
    ConversationOrchestrator(_steps(session_writer=lambda ctx: seen.append(ctx.user_id))
                             ).run_turn("local-user", "hey")
    assert seen == ["local-user"]


def test_recall_hook_uses_configured_default_mode(monkeypatch):
    """default_mode should drive the recall-time ConversationMode, not a hardcoded CASUAL."""
    from types import SimpleNamespace
    import backend.layer2_memory as l2
    from backend.layer2_memory.schemas import ConversationMode

    seen_modes = []

    async def fake_arbiter(user_id, query, emotion, mode, now, store, embedder):
        seen_modes.append(mode)
        return SimpleNamespace(recalled_memories=[])

    # build_pipeline_steps does `from backend.layer2_memory import memory_arbiter` at call
    # time, so patching the attribute on the package before calling it is what takes effect.
    monkeypatch.setattr(l2, "memory_arbiter", fake_arbiter)

    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore(),
                                 default_mode="goal_planning")
    steps.recall("local-user", SimpleNamespace(raw_message="hi"))
    assert seen_modes == [ConversationMode.GOAL_PLANNING]


def test_recall_favors_distressed_memory_when_input_packet_signals_vulnerability():
    """recall_scorer's mood-congruent component (beta=0.30) should track Layer 1's
    composite_emotional_prior, not a hardcoded neutral vector -- otherwise it systematically
    favors neutral-toned memories every turn, backwards from the documented intent."""
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from backend.layer2_memory.schemas import EpisodicMemory, EmotionVector

    store = InMemoryMemoryStore()
    now = datetime.now(timezone.utc)
    common = dict(embedding=[1.0, 1.0, 1.0], S_current=1.0, importance_score=0.5,
                 decay_rate=0.05, created_at=now, user_id="u1")
    distressed = EpisodicMemory(summary="the distressed one",
                                emotion_vector=EmotionVector(valence=-0.7, arousal=0.8), **common)
    neutral = EpisodicMemory(summary="the neutral one",
                             emotion_vector=EmotionVector(valence=0.0, arousal=0.0), **common)
    store.save_episodic(distressed)
    store.save_episodic(neutral)

    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm, memory_store=store)

    high_vulnerability = SimpleNamespace(raw_message="hey", composite_emotional_prior=0.8,
                                         prior_confidence=0.9)
    recalled = steps.recall("u1", high_vulnerability)
    assert recalled and recalled[0].memory.summary == "the distressed one"

    low_vulnerability = SimpleNamespace(raw_message="hey", composite_emotional_prior=0.05,
                                        prior_confidence=0.9)
    recalled = steps.recall("u1", low_vulnerability)
    assert recalled and recalled[0].memory.summary == "the neutral one"


def test_perceive_uses_profile_provider_instead_of_cold_start():
    """A wired profile_provider should make Layer 1 see real history, not a fresh cold start."""
    from datetime import datetime, timezone

    last_end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def fake_profile_provider(user_id):
        return {
            "total_sessions": 12,
            "relationship_age_days": 40,
            "average_session_frequency_days": 3.3,
            "typical_bands": {"evening": 0.8, "morning": 0.2},
            "last_session_end": last_end,
            "message_length_median_chars": 55,
        }

    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore(),
                                 profile_provider=fake_profile_provider)
    now = datetime(2026, 1, 5, tzinfo=timezone.utc)
    packet = steps.perceive("local-user", "hey", now, "session-1")

    assert packet.cold_start_profile is False
    assert packet.total_sessions_with_user == 12
    assert packet.relationship_age_days == 40
    assert packet.gap_category != "same_session"   # 4 days since last_session_end, not fresh


def test_perceive_wired_profile_activates_anomaly_detection():
    """detect_temporal_anomaly returns early below ANOMALY_MIN_SESSIONS (5) — before this phase's
    wiring fix, cold_start_profile was always True and it never ran live at all. With a real
    profile (total_sessions=12) it must actually evaluate, using the derived cadence/histogram."""
    from datetime import datetime, timezone

    def fake_profile_provider(user_id):
        return {
            "total_sessions": 12,
            "relationship_age_days": 30,
            "average_session_frequency_days": 1.0,   # this user messages roughly daily
            "typical_bands": {"evening": 1.0},        # never seen a morning message
            "last_session_end": datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc),
            "message_length_median_chars": 40,
        }

    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore(),
                                 profile_provider=fake_profile_provider)
    # 10 days later (>> 1.0 * 2.5 day threshold) and in the morning (never-seen band).
    now = datetime(2026, 1, 11, 9, 0, tzinfo=timezone.utc)
    packet = steps.perceive("local-user", "hey", now, "session-2")

    assert packet.anomaly_detected is True
    assert "baseline is every 1.0 days" in packet.context_note
    assert "atypical for this user" in packet.context_note


def test_perceive_falls_back_to_cold_start_when_profile_provider_raises():
    from datetime import datetime, timezone

    def broken_provider(user_id):
        raise RuntimeError("store unavailable")

    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore(),
                                 profile_provider=broken_provider)
    packet = steps.perceive("local-user", "hey", datetime.now(timezone.utc), "session-1")

    assert packet.cold_start_profile is True   # degrades gracefully, never raises (§11)


def test_perceive_without_profile_provider_is_unchanged():
    """No profile_provider configured (e.g. offline/dev) -> the original always-cold-start path."""
    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore())
    from datetime import datetime, timezone
    packet = steps.perceive("local-user", "hey", datetime.now(timezone.utc), "session-1")
    assert packet.cold_start_profile is True


def test_real_layer3_wiring_routes_emotional_turn_to_system2():
    """End-to-end through the REAL orchestrator + assembly.py (not a mocked classify step) --
    the two bugs this phase fixed (mode/conversation_mode, crisis_flag/crisis_active attribute
    mismatches) were invisible to every other test because they all mock `classify`. This is the
    one test that runs Layer 3's actual output through route_system and the crisis veto."""
    import json

    class ClassifyingLLM(FakeLLM):
        def __init__(self):
            super().__init__(reply="a warm reply")
            self.classify_calls = 0
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "Classify the message" in prompt:
                self.classify_calls += 1
                return json.dumps({"primary_label": "sadness", "valence": -0.7, "arousal": 0.6,
                                   "confidence": 0.9, "crisis_flag": False,
                                   "primary_intent": "venting"})
            return self._reply

    llm = ClassifyingLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore())
    # "!" and 15+ words keep the message past heuristic_prefilter's neutral-skip gate regardless
    # of circadian band or the day's exact word count -- isolates the mode/routing wiring itself.
    out = ConversationOrchestrator(steps).run_turn(
        "local-user",
        "I have been feeling really overwhelmed and quite sad lately, and honestly "
        "nothing feels right anymore!")

    assert llm.classify_calls >= 1           # the neutral-skip heuristic didn't swallow the LLM call
    assert out.conversation_mode == "emotional_support"
    assert out.cognitive_system == "system2"
    assert out.refined is True


def test_real_layer7_goal_directive_blocked_in_emotional_support_and_shown_in_goal_planning():
    """Layer 7 architecture doc §6.3 hard-blocks goal references in crisis/emotional_support/
    casual modes and before the relationship stage advances past 'new'. api/assembly.py's
    _goal_directive predates the real SC-4 decide_goal_reference reaching the live path (its
    output is computed post-turn -- see POLISH_BACKLOG.md), so these blocks are enforced
    directly in the directive rather than left unenforced. This runs the REAL orchestrator so a
    regression here (e.g. dropping a block) is caught end-to-end, not just at the unit level."""
    import json
    from types import SimpleNamespace

    class ClassifyingLLM(FakeLLM):
        def __init__(self, primary_intent):
            super().__init__(reply="a warm reply")
            self._intent = primary_intent
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "Classify the message" in prompt:
                return json.dumps({"primary_label": "sadness", "valence": -0.7, "arousal": 0.6,
                                   "confidence": 0.9, "crisis_flag": False,
                                   "primary_intent": self._intent})
            return self._reply

    def _rel_provider(stage):
        def _p(user_id):
            return SimpleNamespace(stage=stage, total_messages_exchanged=10, total_sessions=5)
        return _p

    captured = []

    class CapturingClassifyingLLM(ClassifyingLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "Semantic Planner" in prompt:
                captured.append(prompt)
            return super().complete(prompt, system=system, temperature=temperature,
                                    max_tokens=max_tokens)

    # Same emotional_support scenario, capturing the planner prompt directly.
    llm2 = CapturingClassifyingLLM("venting")
    steps2 = build_pipeline_steps(system1=llm2, system2=llm2, embed=llm2,
                                  memory_store=InMemoryMemoryStore(),
                                  goal_provider=lambda uid, msg: ["Run a 5K"],
                                  relationship_provider=_rel_provider("developing"))
    ConversationOrchestrator(steps2).run_turn(
        "local-user",
        "I have been feeling really overwhelmed and quite sad lately, and honestly "
        "nothing feels right anymore!")
    assert captured, "planner was never invoked"
    assert not any("Run a 5K" in p for p in captured), "goal referenced in a blocked mode"

    # goal_planning mode, established relationship: directive should be present.
    captured3 = []

    class GoalPlanningLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "Classify the message" in prompt:
                return json.dumps({"primary_label": "neutral", "valence": 0.1, "arousal": 0.3,
                                   "confidence": 0.9, "crisis_flag": False,
                                   "primary_intent": "goal_setting"})
            if "Semantic Planner" in prompt:
                captured3.append(prompt)
            return self._reply

    llm3 = GoalPlanningLLM()
    steps3 = build_pipeline_steps(system1=llm3, system2=llm3, embed=llm3,
                                  memory_store=InMemoryMemoryStore(),
                                  goal_provider=lambda uid, msg: ["Run a 5K"],
                                  relationship_provider=_rel_provider("developing"))
    ConversationOrchestrator(steps3).run_turn(
        "local-user", "I want to set a new goal for this quarter, can we plan it out?")
    assert captured3, "planner was never invoked"
    assert any("Run a 5K" in p for p in captured3), "goal directive missing in goal_planning mode"

    # goal_planning mode but a brand-new relationship (default stage): blocked by stage.
    captured4 = []

    class GoalPlanningLLM4(GoalPlanningLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "Semantic Planner" in prompt:
                captured4.append(prompt)
            return super().complete(prompt, system=system, temperature=temperature,
                                    max_tokens=max_tokens)

    llm4 = GoalPlanningLLM4()
    steps4 = build_pipeline_steps(system1=llm4, system2=llm4, embed=llm4,
                                  memory_store=InMemoryMemoryStore(),
                                  goal_provider=lambda uid, msg: ["Run a 5K"])  # no relationship_provider -> stage="new"
    ConversationOrchestrator(steps4).run_turn(
        "local-user", "I want to set a new goal for this quarter, can we plan it out?")
    assert captured4, "planner was never invoked"
    assert not any("Run a 5K" in p for p in captured4), "goal referenced for a brand-new relationship"


def test_real_layer4_wiring_forwards_recalled_memories_to_planner_prompt():
    """Layer 2's recalled memories reach ctx.recalled_memories every turn, but plan() in
    api/assembly.py never threaded them into generate_semantic_draft -- the planner LLM
    saw "(no specific memories recalled)" on every single turn regardless of what Layer 2
    actually found. This exercises the real orchestrator + assembly wiring end-to-end and
    also guards against semantic_planner._format_memories falling back to a raw dataclass
    repr (EpisodicMemory's content field is `summary`, not `content`) -- that fallback would
    leak embedding floats and recall scores into the LLM prompt."""
    from datetime import datetime, timezone
    from backend.layer2_memory.schemas import EpisodicMemory, EmotionVector, ScoredMemory

    store = InMemoryMemoryStore()
    now = datetime.now(timezone.utc)
    mem = EpisodicMemory(summary="the user mentioned starting a new job",
                         embedding=[1.0, 1.0, 1.0], S_current=1.0, importance_score=0.5,
                         decay_rate=0.05, created_at=now, user_id="u1",
                         emotion_vector=EmotionVector(valence=0.5, arousal=0.4))
    store.save_episodic(mem)

    captured_prompts = []

    class CapturingLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            captured_prompts.append(prompt)
            return self._reply

    llm = CapturingLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm, memory_store=store)
    ConversationOrchestrator(steps).run_turn("u1", "hey, how's it going")

    planner_prompts = [p for p in captured_prompts if "Semantic Planner" in p]
    assert planner_prompts, "planner was never invoked"
    assert any("the user mentioned starting a new job" in p for p in planner_prompts)
    assert not any("ScoredMemory" in p or "recall_score" in p for p in planner_prompts)


def test_real_layer3_wiring_crisis_flag_reaches_orchestrator_veto():
    """Layer 3's own heuristic crisis detection (no SC-2/Layer-11 involvement) must veto
    generation -- proves the crisis_flag/crisis_active fix without relying on Layer 11 at all."""
    llm = FakeLLM()
    steps = build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                 memory_store=InMemoryMemoryStore())
    out = ConversationOrchestrator(steps).run_turn("local-user", "I just can't go on anymore")
    assert out.crisis_active is True
    assert out.conversation_mode == "crisis"
