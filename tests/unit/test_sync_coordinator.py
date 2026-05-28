# Test: Sync Coordinator
#
# Tests:
#   - Generate encrypted deltas (device A changed this)
#   - Merge deltas (device B changed that)
#   - Detect conflicts (both devices changed same memory)
#   - Apply conflict resolution (most recent wins, or user decides)
#   - Server never sees plaintext (zero-knowledge sync)
#
# Fixtures: db_session, encryption_keys
