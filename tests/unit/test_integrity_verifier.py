# Test: Integrity Verifier
#
# Tests:
#   - Compute Merkle hash tree of all stores
#   - Detect tampering (hash mismatch)
#   - Alert user if corruption found
#   - Perform daily integrity checks
#   - Support recovery (restore from backup if corrupted)
#
# Fixtures: db_session, sample_memories
