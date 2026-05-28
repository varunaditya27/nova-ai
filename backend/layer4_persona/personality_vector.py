# Layer 4, Sub-Component: Personality Vector
#
# Responsibility: Represent Nova's learned personality as a living data structure.
# Read at session start. Updated at session end (post-session only, never during inference).
#
# Core design: Personality is not a static prompt. It is a learned vector with:
#   - Individual belief entries (each with centrality score, confidence, last-updated timestamp)
#   - Dimension vectors for communication style
#   - Emotional baseline calibrated to this user
#   - An adaptation history showing how personality has drifted
#
# Main functions:
#   - load_current_vector(user_id, session_id) -> PersonalityVector
#   - get_core_identity_anchors() -> dict[str, Belief]  # high-centrality beliefs
#   - get_dynamic_properties() -> dict[str, Belief]  # lower-centrality, evolving beliefs
#   - update_belief(belief_id, new_value, evidence_strength) -> None
#   - should_update_personality(evidence_strength, current_belief) -> bool
#
# Integration:
#   - Read by prompt_builder.py to construct system prompt
#   - Updated by state_updater.py at session end
#   - Updated by drift_controller.py's over-adaptation guard
#
# Design principle: High-centrality beliefs require very strong evidence to update (> 0.905).
# Low-centrality beliefs update faster, allowing adaptation without losing core identity.
