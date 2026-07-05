from datetime import datetime, timezone
from uuid import uuid4

from backend.layer2_memory.schemas import (
    EpisodicMemory, IdentityMemory, SemanticMemory, UserWorldModel,
    EmotionVector, PersonNode, RecallEvent,
)
from infra.db.memory_serde import to_jsonable, from_jsonable


def _roundtrip(tp, obj):
    return from_jsonable(tp, to_jsonable(obj))


def test_episodic_roundtrip_full_fidelity():
    m = EpisodicMemory(
        user_id=uuid4(), session_id=uuid4(), summary="hiking trip",
        embedding=[0.1, 0.2, 0.3], topic_tags=["outdoors"], created_at=datetime.now(timezone.utc),
        emotion_vector=EmotionVector(valence=0.4, arousal=0.2, dominant_label="joy"),
        S_current=0.8, decay_rate=0.01, reinforcement_count=2,
        recall_history=[RecallEvent(recalled_at=datetime.now(timezone.utc), trigger_query="q")],
        source_turn_ids=[uuid4()], is_archived=False, is_deleted=False)
    assert _roundtrip(EpisodicMemory, m) == m


def test_semantic_and_identity_roundtrip():
    s = SemanticMemory(user_id=uuid4(), statement="likes tea", confidence=0.7, evidence_count=3)
    assert _roundtrip(SemanticMemory, s) == s
    i = IdentityMemory(statement="values honesty", is_immutable=True, centrality=0.9)
    assert _roundtrip(IdentityMemory, i) == i


def test_uwm_deep_nesting_roundtrip():
    uwm = UserWorldModel(user_id=uuid4())
    uwm.relationship_graph.people.append(PersonNode(name="Sam", aliases=["Sammy"], mention_count=4))
    uwm.confidence_by_field["profile"] = 0.5
    assert _roundtrip(UserWorldModel, uwm) == uwm


def test_uuid_decoding_is_lenient_for_opaque_string_ids():
    # The pipeline uses a string user_id ("local-user"); the dataclass annotates UUID.
    from uuid import UUID
    from typing import Optional
    assert from_jsonable(Optional[UUID], "local-user") == "local-user"
    real = uuid4()
    assert from_jsonable(UUID, str(real)) == real


def test_missing_fields_fall_back_to_defaults():
    m = from_jsonable(EpisodicMemory, {"summary": "partial"})
    assert m.summary == "partial" and m.embedding == [] and m.reinforcement_count == 0
