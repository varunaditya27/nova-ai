# Test: Cognitive Mode Arbiter
#
# Tests:
#   - Classify user input emotion (valence & arousal)
#   - Route to System 1 (casual) vs System 2 (reasoning)
#   - Routing rules: casual → S1, emotional intensity high → S2, reasoning → S2
#   - Edge case: Mixed emotion (confused + urgent)
#
# Fixtures: db_session, sample_conversations
