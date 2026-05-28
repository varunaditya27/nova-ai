# Layer 2, Sub-Component: Memory Types
#
# Responsibility: Define the five memory type classes with full lifecycle support
# (creation, retrieval, decay, consolidation, archival).
#
# Each memory type has distinct:
#   - Storage backend (ChromaDB for episodic/semantic/identity, SQLite for procedural/identity)
#   - Decay dynamics (episodic decays fast, semantic/identity decay slow, procedural updates on pattern confirmation)
#   - Recall trigger conditions (episodic = query similarity, semantic = explicit fact request, identity = self-model questions)
#
# Classes:
#   - EpisodicMemory: "(date, topic, emotion_vector, importance, embedding)"
#   - SemanticMemory: "(fact_type, value, confidence, last_updated, source_session)"
#   - IdentityMemory: "(belief_type, value, centrality, confidence, evidence_strength, last_updated)"
#   - ProceduralMemory: "(pattern_type, pattern_vector, confidence, application_count)"
#   - WorkingMemory: "(session_id, turn_buffer, char_limit, eviction_policy)"
#
# Design: Each class enforces immutability after persistence. Updates are non-destructive
# (old versions kept in audit trail). Deletions are logical only (flagged as deleted, not removed).
