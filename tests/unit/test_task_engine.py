# Test: Task Engine
#
# Tests:
#   - Break goal into tasks
#   - Tasks are achievable (not too granular, not too coarse)
#   - Update task status (pending → in progress → complete)
#   - Handle task dependencies (task B blocked by task A)
#
# Fixtures: db_session, sample_goals
