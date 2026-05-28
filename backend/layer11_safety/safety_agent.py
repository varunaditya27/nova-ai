# Layer 11, Sub-Component: Safety Agent
#
# Responsibility: Entry point for all safety operations. Runs FIRST on every turn.
#
# Workflow:
#   1. Receive user message
#   2. Run crisis_classifier in parallel with Layer 1
#   3. If crisis signal detected, route to escalation_engine
#   4. If no crisis, proceed with normal pipeline
#   5. Post-response, run safe_mode_enforcer (enforces constraints)
#   6. Log all safety decisions
#
# Main functions:
#   - run_safety_check(user_id, message_text, context) -> SafetyResult
#   - route_based_on_safety(result: SafetyResult) -> PipelineRoute
#
# Integration:
#   - Called first by conversation_orchestrator (before Layer 1)
#   - Runs in parallel with main pipeline (never blocks)
#   - Has veto authority: CRISIS or IMMINENT → discard main response, use crisis response
#   - Logs all operations to Layer 12 audit trail
#
# Design: Safety is not an afterthought. It's the first thing that runs.
