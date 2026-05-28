# Schemas for Layer 2 — Memory & Cognition
#
# Defines all data structures for memory types, scoring, recall, consolidation, and auditing.
#
# Five Memory Types:
#   1. EpisodicMemory: Meaningful past interactions, structured summaries (not verbatim transcripts)
#   2. SemanticMemory: Factual knowledge about the user (name, occupation, preferences, known relationships)
#   3. IdentityMemory: Beliefs about who the user is, personality traits, values, goals (Nova's model of the user's self-concept)
#   4. ProceduralMemory: Learned patterns (typing style, communication preferences, decision-making patterns)
#   5. WorkingMemory: Current session buffer, in-flight context, immediate conversation history
#
# Key schemas:
#   - MemoryObject: Base class for all memory types
#   - EpisodicMemory: Time-indexed episode with emotion vector, topic tags, importance score
#   - RecallScore: Multi-dimensional score output from recall_scorer
#   - RecallEvent: Log entry tracking when/how memory was recalled and used
#   - ConsolidationResult: Output of forgetting engine's consolidation sweep
#   - GateDecision: Context gate output (suppress/amplify factor)
#
# Design: All memory objects are time-indexed and support edit/decay/expiration workflows.
# No memory is ever permanently deleted—only downgraded to lower importance or flagged for archival.
