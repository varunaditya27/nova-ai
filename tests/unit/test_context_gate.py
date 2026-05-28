# Test: Context Gate
#
# Tests:
#   - Open gate on high-salience queries
#   - Close gate on low-salience queries (don't waste LLM context)
#   - Handle mixed salience (some high, some low)
#   - Edge case: User asks about something just discussed (high recency)
#
# Fixtures: db_session, sample_memories
