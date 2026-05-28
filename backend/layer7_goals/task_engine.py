# Layer 7, Sub-Component: Task Engine
#
# Responsibility: Decompose goals into executable TaskPlans with dependencies.
#
# Not all goals need task plans. Simple goals (e.g., "read more") don't.
# Complex goals (e.g., "change careers") decompose into abstract, then concrete steps.
#
# Main functions:
#   - generate_task_plan(goal: GoalObject, context) -> TaskPlan
#   - decompose_to_steps(goal, abstraction_level) -> list[TaskStep]
#   - detect_blocking_steps(task_plan) -> list[TaskStep]
#   - detect_circular_dependencies(task_plan) -> bool
#   - suggest_next_step(goal_id) -> TaskStep | None
#
# Integration:
#   - Called post-session via goal_lifecycle or user request
#   - Reads from Layer 7 goal context
#   - May call LLM for decomposition (optional, for complex goals)
#   - Output used by Layer 6 (proactivity) for milestone tracking
#
# Design: Tasks are suggestions, not requirements. User maintains agency.
# Task plans can be accepted, modified, or rejected.
