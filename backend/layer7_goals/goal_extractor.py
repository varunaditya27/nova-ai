# Layer 7, Sub-Component: Goal Extractor
#
# Responsibility: Detect goals from unstructured conversation and formalize them.
#
# Detects three types of goals:
#   1. Explicit: "I want to..." "I'm trying to..." "My goal is..."
#   2. Inferred: "I messed up X again" (implicit goal to stop X); "I wish I were..." (implicit aspiration goal)
#   3. Pattern-derived: Recurring mention of same challenge → detected as goal
#
# Main functions:
#   - extract_goals_from_message(user_message, context) -> list[GoalObject]
#   - run_goal_extraction_async(session_id) -> list[GoalObject]  # post-session
#   - update_goal_importance(goal_id, new_importance) -> None
#
# Integration:
#   - Called asynchronously by state_updater post-session (does not block response)
#   - Calls LLM (groq or ollama) to classify goal signals
#   - Calls goal_lifecycle to create new goals
#   - Reads from Layer 2 (prior goal history) to detect patterns
#
# Design: Goals are extracted opportunistically. No interrogation.
# If signals are ambiguous, goal is not created; wait for more data.
