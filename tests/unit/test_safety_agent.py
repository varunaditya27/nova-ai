# Test: Safety Agent
#
# Tests:
#   - Runs FIRST on every turn
#   - Has veto authority (can reject pipeline output)
#   - Classify crisis level: NONE, MONITORING, ELEVATED, CRISIS, IMMINENT
#   - Route to appropriate escalation tier
#
# Fixtures: db_session, sample_conversations
