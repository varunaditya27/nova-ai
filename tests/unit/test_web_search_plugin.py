"""Tests for the Web Search plugin (architecture doc §9.5)."""

from datetime import datetime, timedelta

from backend.layer8_tools.plugins.web_search_plugin import WebSearchPlugin
from backend.layer8_tools.schemas import ActionType, ConfirmationTier, ToolOutcome

NOW = datetime(2026, 6, 28, 12, 0)


def _backend(results):
    calls = {"n": 0}

    def fn(query):
        calls["n"] += 1
        return results
    return fn, calls


def test_search_parses_results():
    fn, _ = _backend([{"title": "T", "url": "https://ex.com", "snippet": "s"}])
    res = WebSearchPlugin(search_fn=fn).execute("search", {"query": "python", "now": NOW})
    assert res.outcome == ToolOutcome.SUCCESS.value
    assert res.data[0]["title"] == "T" and res.data[0]["url"] == "https://ex.com"


def test_no_results_handled_gracefully():
    fn, _ = _backend([])
    res = WebSearchPlugin(search_fn=fn).execute("search", {"query": "zzz", "now": NOW})
    assert res.outcome == ToolOutcome.SUCCESS.value and res.data == []


def test_spam_and_ads_filtered():
    fn, _ = _backend([
        {"title": "Good", "url": "https://ex.com", "snippet": "s"},
        {"title": "Buy now", "url": "https://spam.example/ad", "snippet": "x", "is_ad": True},
    ])
    res = WebSearchPlugin(search_fn=fn).execute("search", {"query": "q", "now": NOW})
    assert len(res.data) == 1 and res.data[0]["title"] == "Good"


def test_cache_avoids_repeat_within_one_hour():
    fn, calls = _backend([{"title": "T", "url": "https://ex.com", "snippet": "s"}])
    p = WebSearchPlugin(search_fn=fn)
    p.execute("search", {"query": "python", "now": NOW})
    p.execute("search", {"query": "python", "now": NOW + timedelta(minutes=30)})
    assert calls["n"] == 1     # second call served from cache


def test_cache_expires_after_one_hour():
    fn, calls = _backend([{"title": "T", "url": "https://ex.com", "snippet": "s"}])
    p = WebSearchPlugin(search_fn=fn)
    p.execute("search", {"query": "python", "now": NOW})
    p.execute("search", {"query": "python", "now": NOW + timedelta(hours=2)})
    assert calls["n"] == 2


def test_search_is_auto_read_only_tier():
    cap = WebSearchPlugin().capability_for("search")
    assert cap.default_tier == ConfirmationTier.AUTO.value
    assert cap.action_type == ActionType.SEARCH.value


def test_synthesize_uses_injected_llm():
    p = WebSearchPlugin(llm_fn=lambda prompt: "a summary")
    res = p.execute("synthesize_results", {
        "query": "q", "results": [{"title": "T", "snippet": "s"}]})
    assert res.data == "a summary"
