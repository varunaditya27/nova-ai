# Layer 2, Sub-Component: Recall Scorer
#
# Responsibility: Implement the four-signal scoring formula that determines how strongly
# a memory should be recalled given a query, context, and time since last access.
#
# Formula: Score(m, q, e, t) = α·semantic_sim(m, q) + β·emotional_congruence(m, e) 
#                              + γ·temporal_recency(m, t) + δ·importance(m)
#
# Where:
#   α, β, γ, δ are tunable weights from config/layer2.yaml
#   semantic_sim: cosine distance in embedding space (0-1)
#   emotional_congruence: valence/arousal match between memory and current emotion (0-1)
#   temporal_recency: time-decay function; recent memories score higher
#   importance: pre-computed importance flag from episodic memory
#
# Main functions:
#   - score_memory(memory, query, emotion, timestamp) -> RecallScore
#   - score_batch(memories, query, emotion, timestamp) -> list[RecallScore]
#
# Integration:
#   - Called by competitive_recall before softmax
#   - Reads weights from config/layer2.yaml at startup
#   - No LLM calls; purely algorithmic
