# Test: Thread Tracker
#
# Tests:
#   - Track thread state across messages
#   - Detect resolved threads (user says "done")
#   - Cascade resolution to related threads
#   - Track pending thread count
#
# Fixtures: db_session, test_user, sample_conversations
