# Layer 13, Sub-Component: Graduation Evaluator
#
# Responsibility: Evaluate whether cold start criteria are met for graduation.
#
# Graduation criteria (from config/layer13.yaml):
#   - Minimum messages in cold start period (e.g., 5 messages)
#   - Minimum time elapsed (e.g., 3 days, or immediate if 5 messages)
#   - Sufficient context gathered (personality, emotional baseline, some memories)
#   - User hasn't abandoned system (activity check)
#
# Main functions:
#   - evaluate_graduation_readiness(user_id) -> GraduationReport
#   - check_all_criteria(user_id) -> dict[criterion: bool]
#   - is_ready_to_graduate(user_id) -> bool
#   - trigger_graduation(user_id) -> None
#
# Integration:
#   - Called by cold_start_engine post-session
#   - Checks criteria against config/layer13.yaml
#   - Generates graduation report (what was learned)
#   - Calls cold_start_engine.graduate_user() if ready
#
# Design: Graduation is automatic (not user-triggered).
# When system has enough context, cold start ends and full features unlock.
