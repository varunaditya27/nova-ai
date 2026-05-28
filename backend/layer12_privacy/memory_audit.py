# Layer 12, Sub-Component: Memory Audit
#
# Responsibility: Make transparent what Nova actually knows about the user.
#
# User can query:
#   - "Show me everything you know about [person]"
#   - "Show me all memories tagged with [topic]"
#   - "Show me my emotional arc over the past month"
#   - "Show me my goals and their status"
#   - "Show me what you think my values are"
#
# Main functions:
#   - generate_audit_view(user_id, query_type, query_scope) -> MemoryAuditView
#   - query_memories(query: str) -> list[Memory]
#   - correct_memory(memory_id, correction) -> CorrectionResult
#   - downgrade_importance(memory_id) -> None
#   - expire_memory(memory_id, date) -> None
#   - anchor_memory(memory_id, anchor_reason) -> None
#
# Integration:
#   - User-facing API via api/routes/memory.py
#   - Reads from all memory stores
#   - Returns formatted, human-readable output
#   - Never returns raw embeddings or internal scores
#
# Design: Audit interface is user-friendly, not technical. Everything is explainable.
