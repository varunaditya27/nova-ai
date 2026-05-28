# Integration Test: Full System 2 Pipeline
#
# Scenario: User asks reasoning question → System 2 → Response with reasoning
#
# Tests:
#   - Entire pipeline completes in < 30 seconds
#   - Empathy hypothesis generated
#   - Semantic planning executed
#   - LLM reasoning applied
#   - Memories updated
#   - Relationships considered
#   - Response respects persona constraints
#
# Fixtures: db_session, test_user, mock_groq_client
