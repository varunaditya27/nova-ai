# Layer 7 — Goals & Accountability Engine
#
# Core question: What does the user want to achieve, and is Nova tracking it?
#
# This layer tracks meaningful, self-directed intentions expressed in conversation.
# Not a task manager. Not a planner. An accountability engine for life intentions.
#
# Examples of Layer 7 goals:
#   - "I really want to get fit before summer"
#   - "I've been trying to cut back on drinking and it's hard"
#   - "I want to read more"
#   - "I need to fix things with my brother"
#
# Not mentioned to a goal system. Mentioned in conversation. Layer 7 captures the intention.
#
# Central claim: Goals are the thread of future-directed meaning. Holding them makes Nova
# genuinely invested in where the user is going, not just empathetic about where they are.
#
# Main components:
#   - goal_lifecycle.py: GoalObject state machine (active → paused → complete → abandoned)
#   - goal_extractor.py: Explicit/inferred/pattern-derived goal detection
#   - task_engine.py: TaskPlan, TaskStep, dependency graphs, blocking logic
#   - conflict_detector.py: Resource/value/identity/temporal conflict detection
#   - life_event_tracker.py: LifeEvent detection + cascade to Goals/Memory/Relationship
#   - schemas.py: GoalObject, TaskPlan, TaskStep, ConflictObject, LifeEvent
#
# Contract: Goals are read-only during inference. Updates happen post-session via state_updater.
