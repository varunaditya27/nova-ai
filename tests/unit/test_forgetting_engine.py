# Test: Forgetting Engine
#
# Tests:
#   - Decay formula: importance = importance × (0.92 ^ sessions_since_access)
#   - Run decay sweep and verify older memories decay more
#   - Clustering: Group similar topics
#   - Compression: Summarize clusters without losing signal
#
# Fixtures: db_session, sample_memories_with_age
