# Layer 13, Sub-Component: Cold Start Engine
#
# Responsibility: Orchestrate the entire onboarding arc. Entry point for Layer 13.
#
# Workflow:
#   1. User sends first message
#   2. Cold Start Engine activates (overlays normal pipeline)
#   3. Adds constraints: passive elicitation begins, no complex features yet
#   4. Each session, evaluates graduation criteria
#   5. When criteria met: Cold Start Engine self-terminates
#   6. Normal pipeline takes full control
#
# Main functions:
#   - check_cold_start_status(user_id) -> ColdStartState
#   - activate_cold_start(user_id) -> None
#   - run_cold_start_overlay(pipeline_context) -> ConstrainedContext
#   - evaluate_graduation(user_id) -> GraduationReport
#   - graduate_user(user_id) -> None
#
# Integration:
#   - Called by conversation_orchestrator at session start
#   - May modify context/constraints on active user
#   - Triggers graduation_evaluator post-session
#   - Self-disables after graduation
#
# Design: Cold start is a temporary overlay. Once graduated, user gets full system.
