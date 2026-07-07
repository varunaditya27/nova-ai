"""Echo projection unwraps Layer-2 ScoredMemory wrappers and bare memories alike."""
from types import SimpleNamespace

from api.echoes import project_echoes


def test_unwraps_scored_memory_with_fuzzy_label():
    scored = SimpleNamespace(
        memory=SimpleNamespace(summary="you'd regret Mongo", created_at=None),
        fuzzy_temporal_label="a few weeks ago")
    out = project_echoes([scored])
    assert out == [{"summary": "you'd regret Mongo", "when": "a few weeks ago", "created_at": None}]


def test_accepts_bare_memory_object():
    out = project_echoes([SimpleNamespace(content="raw content", created_at=None)])
    assert out[0]["summary"] == "raw content" and out[0]["when"] is None


def test_skips_empty_and_caps_at_three():
    items = [SimpleNamespace(memory=SimpleNamespace(summary=s)) for s in ["a", "", "b", "c", "d"]]
    out = project_echoes(items)
    assert [e["summary"] for e in out] == ["a", "b", "c"]      # empty skipped, capped at 3
