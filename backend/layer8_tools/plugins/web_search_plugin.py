# Web Search Plugin
#
# Provides web search with result filtering, extraction, and synthesis.
#
# Actions:
#   - search(query) -> list[SearchResult]
#   - extract_content(url) -> str
#   - synthesize_results(results, query) -> str
#
# Implementation notes:
#   - Uses a public search API (Bing, Google Custom Search, DuckDuckGo)
#   - Results are filtered for safety (no malicious sites, etc.)
#   - AUTO confirmation tier (read-only, user can see results immediately)
#   - Optional LLM synthesis for complex queries
#   - No undo needed (read-only)
