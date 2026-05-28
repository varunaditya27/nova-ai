# Layer 2, Sub-Component: Memory Store
#
# Responsibility: Single unified interface for all memory operations.
# Acts as the Memory Arbiter—the only entry point for downstream layers to access memories.
#
# Design principle: All reads go through this store. No layer queries the backend directly.
# All writes go through the State Updater at session end (not during inference).
#
# Main operations:
#   - query_episodic(user_id, query_text, top_k=10) -> list[EpisodicMemory]
#   - query_semantic(user_id, fact_type) -> list[SemanticMemory]
#   - query_identity(user_id, dimension) -> list[IdentityMemory]
#   - get_working_memory_buffer(session_id) -> WorkingMemoryBuffer
#   - store_episodic(memory: EpisodicMemory) -> memory_id
#   - store_semantic(memory: SemanticMemory) -> memory_id
#   - update_importance(memory_id, new_importance_score) -> None
#   - mark_for_consolidation(memory_id) -> None
#
# Integration:
#   - Calls vector_store (ChromaDB) for semantic/episodic retrieval
#   - Reads from infra.db.models for SQLite persistence
#   - Never calls LLM directly (all LLM calls are in processing layer components)
