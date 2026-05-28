# Layer 5, Sub-Component: Tie Strength Calculator
#
# Responsibility: Compute a single 0.0–1.0 tie strength score from multiple interaction signals.
#
# Tie strength reflects closeness and importance. It is computed from:
#   - Communication frequency (how often mentioned recently)
#   - Relationship duration (how long user has known them)
#   - Vulnerability/disclosure level (what they share with this person)
#   - Emotional intensity of interactions (are conversations deep or surface?)
#   - Reciprocity (does user feel the relationship is mutual?)
#   - Uniqueness (is this relationship one-of-a-kind or fungible?)
#
# Formula is learned (possibly via simple linear regression) on labeled data.
# All weights tuned to config/layer5.yaml.
#
# Main functions:
#   - compute_tie_strength(relationship_state, interaction_history) -> TieStrength
#   - update_tie_strength(relationship_id) -> TieStrength
#   - recalculate_all_tie_strengths(user_id) -> None
#
# Integration:
#   - Called after any relationship update
#   - Feeds tie strength into relationship_manager's state
#   - Used by social_coaching to calibrate advice
#   - Used by layer6 to calibrate proactive message timing
#
# Design: Tie strength is computed, not assigned. It evolves as relationship description evolves.
