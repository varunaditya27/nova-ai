# Test: Prompt Builder
#
# Tests:
#   - Build system prompt from personality vector
#   - Verify prompt includes persona constraints
#   - Verify prompt doesn't leak user data
#   - Regenerate on personality change
#
# Fixtures: db_session, personality_vector
