"""The user's reply to an onboarding question is learned — and a known answer is never re-asked."""
import json

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.elicitation import select_elicitation
from api.state import build_app_state
from infra.db.engine import init_db
from infra.db.initial_state_store import PostgresInitialStateStore
from infra.db.onboarding_store import PostgresOnboardingStore


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        if "asked the user" in prompt:
            return json.dumps({"answer": "feeling lonely at college"})
        return "ok"
    def stream(self, prompt, **k):
        yield "ok"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _state():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    return build_app_state(
        config={"system": {"default_user_id": "u1"}, "llm": {}, "memory": {},
                "onboarding": {"graduation_sessions": 5}},
        llm_clients=clients, engine=engine, vector_store=object())


def test_reply_to_the_question_is_captured_into_initial_state():
    state = _state()
    PostgresOnboardingStore(state.session_factory, "u1").record_elicitation(
        "s1", "primary_reason", "hey there")
    state.orchestrator.run_turn("u1", "honestly I just feel pretty lonely lately", session_id="s1")
    assert PostgresInitialStateStore(state.session_factory, "u1").load().primary_reason \
        == "feeling lonely at college"


def test_the_asking_turn_is_not_mistaken_for_the_answer():
    state = _state()
    store = PostgresOnboardingStore(state.session_factory, "u1")
    store.record_elicitation("s1", "primary_reason", "hey there")
    state.orchestrator.run_turn("u1", "hey there", session_id="s1")
    assert PostgresInitialStateStore(state.session_factory, "u1").load().primary_reason is None
    assert store.take_pending_answer("something else") == "primary_reason"   # still pending


def test_known_targets_are_never_asked_again():
    asked = select_elicitation("I have exams next week", 2, [], False)
    assert asked is not None and asked.inference_target == "life_phase"
    again = select_elicitation("I have exams next week", 2, [], False, known_targets=["life_phase"])
    assert again is None or again.inference_target != "life_phase"


def test_a_mood_is_never_taken_for_the_users_name():
    from backend.layer13_onboarding.context_constructor import extract_name
    for message in ("I'm tired", "i'm feeling low", "I'm Sorry, long day", "I'm a student"):
        assert extract_name(message) is None
    assert extract_name("Hi, I'm Arjun") == "Arjun"
    assert extract_name("my name is meera") == "Meera"


def test_learned_name_and_life_stage_reach_the_persona_prompt():
    state = _state()
    state.orchestrator.run_turn("u1", "Hi, I'm Arjun and I have my engineering exams next week",
                                session_id="s1")
    state.post_turn.shutdown()
    from api.state import make_uwm_provider
    profile = make_uwm_provider(state.session_factory)("u1").profile
    assert profile.preferred_name == "Arjun" and profile.current_life_stage == "student"
