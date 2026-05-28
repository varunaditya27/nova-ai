# Schemas for Layer 7 — Goals & Accountability Engine
#
# Defines goal objects, task plans, conflicts, and life events.
#
# Key schemas:
#   - GoalObject: A meaningful self-directed intention
#     (goal_id, description, state, abstraction_level, deadline, created_at, last_discussed_at,
#      progress_percentage, completion_proof, conflict_flags)
#   - GoalState: Enum (active, paused, complete, abandoned, someday)
#   - AbstractionLevel: Enum (1=concrete, 2=milestone, 3=abstract; e.g., "drink less tea" → "better health" → "wellbeing")
#   - TaskPlan: Decomposition of a goal into steps
#   - TaskStep: Individual action with estimated effort, dependencies, completion status
#   - ConflictObject: Resource/value/identity/temporal conflict (goal_id1, goal_id2, conflict_type, severity)
#   - LifeEvent: Significant life event detected (event_type, description, date, affected_goals)
#
# Design: Goals evolve through conversation, not through structured entry.
# Conflicts are detected automatically and surfaced for user awareness.
# All goal state changes are logged and auditable.
