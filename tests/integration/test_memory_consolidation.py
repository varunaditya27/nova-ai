# Integration Test: Memory Consolidation
#
# Scenario: User has 1 month of memories → Consolidation runs → Decay applied
#
# Tests:
#   - Older memories decay more (0.92 ^ sessions_since_access)
#   - Memories are clustered
#   - Clusters are compressed (summaries generated)
#   - Important memories retained
#   - Recall still works post-consolidation
#   - Total storage reduced
#
# Fixtures: db_session, sample_memories_one_month
