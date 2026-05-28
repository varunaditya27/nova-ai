# Layer 6, Sub-Component: Check-In Engine
#
# Responsibility: Evaluate which proactive outreach opportunities are valid and score their urgency.
#
# Input: All potential check-in triggers from upstream layers:
#   - From Layer 1: Overdue/due-today narrative threads, temporal anomalies
#   - From Layer 2: Episodic memories with specific emotional valences
#   - From Layer 5: Relationship anniversaries, marked important relationships
#   - From Layer 7: Goal milestones due, goal progress stalled
#   - From Layer 10: Weekly summaries ready, life dimension trends
#
# Main functions:
#   - evaluate_trigger(trigger: CheckInTrigger, context: SessionContext) -> ProactiveItem | None
#   - compute_intrusion_score(item: ProactiveItem) -> IntrusionScore
#   - compute_priority_score(item: ProactiveItem) -> float  # 0–100, higher = more urgent
#   - get_candidates_for_evaluation() -> list[CheckInTrigger]
#
# Integration:
#   - Called by check_in_pipeline every ~30 minutes
#   - Produces ProactiveItem objects fed to notification_policy.py
#   - Intrusion score gates whether item is sent or deferred
#
# Design: Intrusion cost formula prevents message spam even if many triggers fire.
# If user is in crisis or has had lots of recent messages, intrusion cost spikes.
