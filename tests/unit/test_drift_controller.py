# Test: Drift Controller
#
# Tests:
#   - Detect personality drift (e.g., suddenly extremely sarcastic)
#   - Enforce boundaries (don't let core values change)
#   - Reject adaptations that violate constraints
#   - Log all drift attempts (for debugging)
#
# Fixtures: db_session, sample_conversations
