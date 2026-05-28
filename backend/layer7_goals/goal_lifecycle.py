# Layer 7, Sub-Component: Goal Lifecycle Manager
#
# Responsibility: State machine for goals—creation, activation, pausing, completion, abandonment.
#
# State transitions:
#   active ← → paused (user explicit or inferred from inactivity)
#   active → complete (user declares done or proof provided)
#   active → abandoned (user explicitly gives up; triggers reflection)
#   any → someday (backlog, not currently being pursued)
#
# Main functions:
#   - create_goal(goal_description, context) -> GoalObject
#   - update_goal_state(goal_id, new_state, rationale) -> GoalObject
#   - mark_goal_complete(goal_id, proof) -> GoalObject
#   - mark_goal_abandoned(goal_id, reason) -> GoalObject
#   - get_active_goals(user_id) -> list[GoalObject]
#
# Integration:
#   - Called by goal_extractor when goals are detected
#   - Called by state_updater post-session
#   - Queried by Layer 4 (prompt building) for goal context
#   - Queried by Layer 6 (proactivity) for milestone check-ins
#   - All transitions logged to audit trail
#
# Design: Goals are not deleted, only marked complete or abandoned.
# Abandonment is treated as meaningful and triggers reflection, not shame.
