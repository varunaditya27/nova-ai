# Test: Goal Extractor
#
# Tests:
#   - Extract goals from natural language ("I want to run a marathon")
#   - Distinguish goal from passing comment
#   - Generate goal objects with metadata
#   - Handle implicit vs explicit goals
#
# Fixtures: db_session, sample_conversations, mock_groq_client
