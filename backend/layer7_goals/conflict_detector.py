# Layer 7, Sub-Component: Conflict Detector
#
# Responsibility: Identify resource/value/identity/temporal conflicts between goals.
#
# Four types of conflicts:
#   1. Resource: Two goals compete for same time/energy (e.g., "get fit" vs. "sleep more")
#   2. Value: Goals embody conflicting values (e.g., "make lots of money" vs. "spend time with family")
#   3. Identity: Goals imply contradictory self-concepts (e.g., "be outgoing" vs. "be private")
#   4. Temporal: Goals have incompatible timelines (e.g., "travel for 6 months" vs. "start new job next month")
#
# Main functions:
#   - detect_conflicts(user_id) -> list[ConflictObject]
#   - classify_conflict_type(goal1, goal2) -> ConflictType
#   - compute_conflict_severity(goal1, goal2, conflict_type) -> float  # 0–1
#   - suggest_resolution(conflict: ConflictObject) -> ResolutionSuggestion
#
# Integration:
#   - Called post-goal-creation and weekly via background job
#   - Reads from Layer 7 (all goals), Layer 5 (values/relationships)
#   - Conflicts surfaced to user for awareness and resolution
#   - Integrated into Layer 6 proactivity (gentle coaching)
#
# Design: Conflicts are not failures. They're part of being human.
# Layer 7 surfaces them for user awareness and resolution.
