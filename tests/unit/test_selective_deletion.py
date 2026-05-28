# Test: Selective Deletion
#
# Tests:
#   - Delete by type: forget_person, forget_topic, forget_session, forget_emotion, full_reset
#   - Apply grace period for undo (default 30 days)
#   - Validate deletion cascades correctly
#   - Log deletion for audit
#
# Fixtures: db_session, sample_memories
