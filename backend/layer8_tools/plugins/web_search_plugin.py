"""Web Search plugin (architecture doc §9.5).

Read-only search with safety filtering, a 1-hour result cache (don't re-hit the API for the
same query within the hour), and optional LLM synthesis. The search backend (``search_fn``)
and synthesis model (``llm_fn``) are injected so the plugin runs offline; both default to safe
no-ops. Search is AUTO — read-only, the user sees results immediately, nothing to undo.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.schemas import (
    ActionType,
    Capability,
    ConfirmationTier,
    ToolOutcome,
    ToolResult,
)

_CACHE_TTL = timedelta(hours=1)
_SPAM_MARKERS = ("/ad", "spam", "doubleclick", "tracker")


class WebSearchPlugin(ToolPlugin):
    name = "web_search"

    def __init__(
        self,
        search_fn: Optional[Callable[[str], list]] = None,
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._search_fn = search_fn or (lambda query: [])
        self._llm_fn = llm_fn
        self._cache: dict[str, tuple[datetime, list]] = {}  # query -> (fetched_at, results)

    def capabilities(self) -> list[Capability]:
        return [
            Capability("search", ActionType.SEARCH.value, "Search the web",
                       default_tier=ConfirmationTier.AUTO.value, required_params=["query"]),
            Capability("extract_content", ActionType.READ.value, "Extract page content",
                       default_tier=ConfirmationTier.AUTO.value, required_params=["url"]),
            Capability("synthesize_results", ActionType.READ.value, "Summarize results",
                       default_tier=ConfirmationTier.AUTO.value, required_params=["query"]),
        ]

    def execute(self, operation: str, parameters: dict) -> ToolResult:
        parameters = parameters or {}
        if operation == "search":
            return self._search(parameters)
        if operation == "extract_content":
            return ToolResult(self.name, "extract_content", ToolOutcome.SUCCESS.value,
                              data="")
        if operation == "synthesize_results":
            return self._synthesize(parameters)
        return ToolResult(self.name, operation, ToolOutcome.FAILURE.value,
                          error_message=f"unsupported operation: {operation}")

    def _search(self, params: dict) -> ToolResult:
        query = params["query"]
        now = params.get("now") or datetime.utcnow()

        cached = self._cache.get(query)
        if cached and (now - cached[0]) < _CACHE_TTL:
            results = cached[1]
        else:
            results = self._filter(self._search_fn(query) or [])
            self._cache[query] = (now, results)

        return ToolResult(self.name, "search", ToolOutcome.SUCCESS.value,
                          result_summary=f"{len(results)} result(s)", data=results)

    @staticmethod
    def _filter(results: list) -> list:
        """Drop ads and obvious spam/tracker URLs (safety filtering)."""
        clean = []
        for r in results:
            if r.get("is_ad"):
                continue
            url = (r.get("url") or "").lower()
            if any(marker in url for marker in _SPAM_MARKERS):
                continue
            clean.append(r)
        return clean

    def _synthesize(self, params: dict) -> ToolResult:
        if self._llm_fn is None:
            return ToolResult(self.name, "synthesize_results", ToolOutcome.SUCCESS.value,
                              data=None, result_summary="no synthesis model")
        results = params.get("results", [])
        prompt = (f"Summarize these search results for the query '{params['query']}':\n"
                  + "\n".join(f"- {r.get('title', '')}: {r.get('snippet', '')}" for r in results))
        try:
            summary = self._llm_fn(prompt)
        except Exception:
            return ToolResult(self.name, "synthesize_results", ToolOutcome.FAILURE.value,
                              error_message="synthesis failed")
        return ToolResult(self.name, "synthesize_results", ToolOutcome.SUCCESS.value,
                          data=summary)
