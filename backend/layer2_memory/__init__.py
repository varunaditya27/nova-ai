# Layer 2 — Cognition & Memory
#
# This is the cognitive core of NovaAI. Every other layer is downstream of this one working correctly.
#
# Core thesis: Memory is not storage. It is a dynamic signal with strength, decay, emotional resonance,
# and competitive selection. Getting this right makes Nova feel like it genuinely knows you.
#
# Architecture: Organized into three functional groups:
#   1. Storage Group: Five memory types (episodic, semantic, identity, procedural, working)
#   2. Processing Group: Scoring function, competitive recall, context gating, forgetting engine
#   3. State Group: User World Model, cross-session narrative linking, Memory Audit Trail
#
# Main components:
#   - memory_store.py: Unified read/write interface for all memory types
#   - memory_types.py: Data structures for each memory type
#   - recall_scorer.py: 4-signal scoring formula (α β γ δ weights)
#   - competitive_recall.py: Softmax-based probabilistic recall with temperature τ
#   - context_gate.py: Suppression/amplification gates based on context
#   - forgetting_engine.py: Decay sweep, cluster detection, semantic compression
#   - schemas.py: All memory objects, scores, consolidation results
#
# Contract: Every downstream layer reads memories through the Memory Arbiter only.
# No layer queries the store directly. All writes go through State Updater at session end.
