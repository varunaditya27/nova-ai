# Test: Goal Lifecycle
#
# Tests:
#   - State machine: active → paused → complete → abandoned → someday
#   - Transitions are valid (e.g., can't go abandoned → active)
#   - Timestamps are recorded
#   - Handle goal completion with optional celebration
#
# Fixtures: db_session, sample_goals
