# Test: Recall Scorer
#
# Tests:
#   - Four-signal scoring formula: α·semantic + β·emotional + γ·recency + δ·importance
#   - Softmax normalization with temperature τ
#   - Edge cases: All signals zero, conflicting signals
#   - Weight sensitivity: Small changes to α/β/γ/δ shouldn't break ranking
#
# Fixtures: db_session, sample_memories, mock_embedding_fn
