# Layer 6, Sub-Component: Pattern Detector
#
# Responsibility: Identify recurring temporal-emotional cycles across sessions.
#
# Examples of patterns:
#   - Emotional crash every Sunday evening
#   - Work anxiety peaks mid-week
#   - User checks in more frequently before big events
#   - Relationship conflicts follow specific calendar events
#
# This component detects these patterns and flags them for proactive intervention.
#
# Main functions:
#   - detect_patterns(user_id, lookback_weeks=12) -> list[PatternObject]
#   - run_pattern_sweep() -> None  # called weekly by background job
#   - pattern_is_active(pattern_id, current_timestamp) -> bool
#   - suggest_proactive_action(pattern: PatternObject) -> ProactiveItem
#
# Integration:
#   - Runs weekly as background job (memory_consolidation_job.py)
#   - Reads from Layer 2 (emotional history) and Layer 1 (session timestamps)
#   - Produces ProactiveItem objects fed to check_in_engine
#   - Integrates with Layer 6 proactive queue
#
# Design: Patterns must repeat at least 3x to be flagged as significant.
# False positives are suppressed via statistical significance testing.
