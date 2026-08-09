"""Goal accountability + relationship familiarity are injected into the planner prompt."""
import json

import pytest
pytest.importorskip("pydantic")

from backend.pipeline import ConversationOrchestrator
from backend.layer2_memory import InMemoryMemoryStore
from backend.layer4_persona.schemas import RelationshipState
from api.assembly import build_pipeline_steps


class CapturingLLM:
    """Records every prompt the planner builds so we can assert on injected directives.

    Classifies as ``goal_setting`` intent (-> goal_planning conversation mode) so goal
    accountability injection isn't blocked by Layer 7's §6.3 mode gate (crisis/
    emotional_support/casual) -- see test_assembly_turn.py's Phase 7 wiring test for the
    blocked-mode and blocked-stage cases.
    """
    def __init__(self):
        self.prompts = []
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        if "Classify the message" in prompt:
            return json.dumps({"primary_label": "neutral", "valence": 0.1, "arousal": 0.3,
                               "confidence": 0.9, "crisis_flag": False,
                               "primary_intent": "goal_setting"})
        self.prompts.append(prompt)
        return "Sounds good."
    def stream(self, prompt, **k):
        yield "Sounds good."
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _steps(llm, goal_provider=None, relationship_provider=None, uwm_provider=None,
          identity_provider=None):
    return build_pipeline_steps(system1=llm, system2=llm, embed=llm,
                                memory_store=InMemoryMemoryStore(),
                                goal_provider=goal_provider,
                                relationship_provider=relationship_provider,
                                uwm_provider=uwm_provider,
                                identity_provider=identity_provider)


def test_goal_titles_injected_into_prompt():
    """goal_provider now returns the real SC-4 accountability decision (architecture doc §6),
    not bare title strings -- a real persisted Goal, mentioned via a completion-signal phrase,
    proves the directive (which always includes the goal's title, see
    accountability_modifier.py's `packet()` helper) reaches the planner prompt."""
    from datetime import datetime, timezone
    from infra.db import make_engine, make_session_factory, init_db
    from infra.db.goal_store import PostgresGoalStore
    from backend.layer7_goals.schemas import Goal
    from api.state import make_goal_provider

    now = datetime.now(timezone.utc)
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    PostgresGoalStore(factory, "u1").add_goal(
        Goal(title="run a 5k", status="active", last_mentioned_at=now, created_at=now))

    llm = CapturingLLM()
    rel = RelationshipState(stage="developing", total_messages_exchanged=120, total_sessions=20)
    steps = _steps(llm, goal_provider=make_goal_provider(factory, llm),
                  relationship_provider=lambda uid: rel)
    ConversationOrchestrator(steps).run_turn(
        "u1", "I finally did it, I officially finished my goal!", now=now)
    assert any("run a 5k" in p for p in llm.prompts)


def test_relationship_stage_injected_into_prompt():
    llm = CapturingLLM()
    rel = RelationshipState(stage="developing", total_messages_exchanged=120, total_sessions=20)
    steps = _steps(llm, relationship_provider=lambda uid: rel)
    ConversationOrchestrator(steps).run_turn("u1", "hey")
    assert any("developing" in p for p in llm.prompts)


def test_no_providers_still_generates():
    llm = CapturingLLM()
    out = ConversationOrchestrator(_steps(llm)).run_turn("u1", "hi")
    assert out.response_text.strip()


def test_uwm_profile_and_people_injected_into_prompt():
    """Closes the other half of the UWM gap: not just real extraction/merge (see
    tests/unit/api/test_state.py), but the read side actually reaching the planner prompt --
    previously nothing in api/ or backend/layer4_persona/ ever read uwm_context at all."""
    from backend.layer2_memory.schemas import PersonNode, UserWorldModel

    llm = CapturingLLM()
    uwm = UserWorldModel(user_id="u1")
    uwm.profile.preferred_name = "Sam"
    uwm.profile.field_of_study_or_work = "nursing"
    uwm.relationship_graph.people.append(
        PersonNode(name="Maya", relationship_tier="friend", mention_count=3))
    steps = _steps(llm, uwm_provider=lambda uid: uwm)
    ConversationOrchestrator(steps).run_turn("u1", "hey")
    assert any("Sam" in p and "Maya" in p for p in llm.prompts)


def test_uwm_communication_model_not_injected_by_uwm_directive():
    """communication_model is deliberately excluded from the UWM directive -- style_learning.py
    (fed by relationship_provider) already owns communication style live; _uwm_directive must
    never read uwm.communication_model, even when it's populated (with nothing else set, the
    directive must be empty and persona_instruction must stay untouched)."""
    from backend.layer2_memory.schemas import UserWorldModel

    llm = CapturingLLM()
    uwm = UserWorldModel(user_id="u1")
    uwm.communication_model.vocabulary_complexity = "simple"
    uwm.communication_model.uses_humor = True
    steps = _steps(llm, uwm_provider=lambda uid: uwm)
    ConversationOrchestrator(steps).run_turn("u1", "hey")
    assert not any("vocabulary_complexity" in p or "uses_humor" in p for p in llm.prompts)


def test_identity_beliefs_injected_into_prompt():
    """Closes the read half of the Identity Memory gap: identity_provider's top-centrality
    non-immutable beliefs actually reach the planner prompt via build_persona -- previously
    identity_beliefs() had zero callers anywhere in api/ or backend/layer4_persona/."""
    from backend.layer2_memory.schemas import IdentityCategory, IdentityMemory

    llm = CapturingLLM()
    belief = IdentityMemory(category=IdentityCategory.PERSONALITY_TRAIT,
                            statement="Nova is unusually fond of terrible puns", centrality=0.6)
    steps = _steps(llm, identity_provider=lambda uid: [belief])
    ConversationOrchestrator(steps).run_turn("u1", "hey")
    assert any("terrible puns" in p for p in llm.prompts)


def test_immutable_identity_beliefs_never_reach_the_prompt():
    """Immutable safety policies are enforced by Layer 11's separate hard-coded path, not by
    reminding the LLM every turn -- the identity directive must never surface one, even if a
    provider implementation mistakenly includes one in its returned list."""
    from backend.layer2_memory.schemas import IdentityCategory, IdentityMemory

    llm = CapturingLLM()
    immutable = IdentityMemory(category=IdentityCategory.BEHAVIORAL_POLICY,
                               statement="Nova does not provide medical diagnoses",
                               centrality=1.0, is_immutable=True)
    steps = _steps(llm, identity_provider=lambda uid: [immutable])
    ConversationOrchestrator(steps).run_turn("u1", "hey")
    assert not any("medical diagnoses" in p for p in llm.prompts)
