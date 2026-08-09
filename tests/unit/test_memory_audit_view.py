"""Tests for SC-3 Memory Audit — transparency view + query + provenance (architecture doc §5)."""

from datetime import date, datetime
from types import SimpleNamespace

from backend.layer12_privacy import memory_audit as ma
from backend.layer12_privacy.schemas import AuditQueryResult, MemoryAuditView, ProvenanceRecord

NOW = datetime(2025, 6, 1)


def _mem(mid, importance=0.5, anchored=False, tags=None, summary="a chat"):
    return SimpleNamespace(memory_id=mid, importance_score=importance, is_anchored=anchored,
                           topic_tags=tags or [], human_readable_summary=summary,
                           created_at=date(2025, 5, 1), emotion_at_formation="neutral",
                           reinforcement_count=0)


def _fact(fid, text="x", category="preferences"):
    # Real SemanticMemory field names (memory_id/statement/memory_type/supporting_episode_ids) --
    # a prior fact_id/fact_text/category/source_episode_ids shape here matched the audit view's
    # own (now-fixed) bug rather than the real Layer-2 schema; see backend/layer12_privacy/
    # memory_audit.py::_to_auditable_fact.
    return SimpleNamespace(memory_id=fid, statement=text, memory_type=category, confidence=0.8,
                           supporting_episode_ids=["m1"], S_current=1.0, is_deprecated=False)


class _Store:
    def __init__(self, items):
        self._items = items
    def all(self):
        return list(self._items)


# ── Importance labels (§5.2) ─────────────────────────────────────────────────
def test_importance_label_mapping():
    assert ma.map_importance_to_label(0.2, anchored=False) == "Low"
    assert ma.map_importance_to_label(0.5, anchored=False) == "Medium"
    assert ma.map_importance_to_label(0.85, anchored=False) == "High"
    assert ma.map_importance_to_label(0.99, anchored=True) == "Anchored"


# ── Audit view assembly (§5.2) ───────────────────────────────────────────────
def test_generate_audit_view_counts_and_sections():
    view = ma.generate_audit_view(
        "u1", memory_store=_Store([_mem("m1"), _mem("m2")]),
        semantic_store=_Store([_fact("f1")]), now=NOW)
    assert isinstance(view, MemoryAuditView)
    assert view.total_memory_count == 2
    assert len(view.episodic) == 2 and len(view.semantic) == 1
    assert view.semantic[0].fact_id == "f1" and view.semantic[0].fact_text == "x"


def test_generate_audit_view_converts_real_identity_beliefs():
    from backend.layer2_memory.schemas import IdentityCategory, IdentityMemory

    belief = IdentityMemory(statement="Nova values honesty", category=IdentityCategory.CORE_VALUE,
                            centrality=0.9, is_immutable=True)
    view = ma.generate_audit_view("u1", memory_store=_Store([]),
                                  identity_store=_Store([belief]), now=NOW)
    assert len(view.identity) == 1
    got = view.identity[0]
    assert got.fact_id == str(belief.belief_id)
    assert got.fact_text == "Nova values honesty"
    assert got.category == "core_value"
    assert got.is_user_confirmed is True   # is_immutable mapped through


def test_safety_section_is_count_only():
    # safety store exposes a crisis count; the audit view must show no content, only the count.
    view = ma.generate_audit_view(
        "u1", memory_store=_Store([]), safety_store=SimpleNamespace(crisis_session_count=lambda: 3),
        now=NOW)
    assert view.crisis_session_count == 3


# ── Query intent classification (§5.3) ───────────────────────────────────────
def test_intent_temporal():
    assert ma.classify_query_intent("what do you remember from last year?") == "temporal_query"


def test_intent_identity():
    assert ma.classify_query_intent("what do you believe my values are?") == "identity_query"


def test_intent_pattern():
    assert ma.classify_query_intent("what patterns have you noticed about me?") == "pattern_query"


def test_intent_defaults_to_topic():
    assert ma.classify_query_intent("what about my project?") == "topic_query"


# ── Query execution (§5.3) ───────────────────────────────────────────────────
def test_query_returns_matching_records_by_topic():
    store = _Store([_mem("m1", tags=["family"]), _mem("m2", tags=["work"])])
    result = ma.query("tell me what you know about my family", memory_store=store)
    assert isinstance(result, AuditQueryResult)
    assert [r.memory_id for r in result.records] == ["m1"]
    assert result.total_count == 1


# ── Provenance (§5.4) ────────────────────────────────────────────────────────
def test_build_provenance_record():
    mem = _mem("m1")
    prov = ma.build_provenance(mem, primary_session_id="s1")
    assert isinstance(prov, ProvenanceRecord)
    assert prov.memory_id == "m1" and prov.primary_session_id == "s1"
