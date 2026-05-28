# Layer 5, Sub-Component: Relationship Manager
#
# Responsibility: CRUD + state machine for all relationship objects the user has described.
#
# Manages full relationship lifecycle:
#   - Detection: New person mentioned
#   - Initialization: Create SocialNode + RelationshipState
#   - Tracking: Update interaction counts, conflict flags, milestone events
#   - Stage transitions: Acquaintance → Casual → Close (triggered by user description)
#   - Archival: Ended relationships (estranged, lost touch)
#
# Main functions:
#   - create_relationship(person_name, context) -> RelationshipState
#   - update_relationship_state(relationship_id, updates) -> RelationshipState
#   - transition_stage(relationship_id, new_stage, rationale) -> bool
#   - get_relationships(user_id, filter_by_stage) -> list[RelationshipState]
#   - record_interaction(relationship_id, interaction_type, notes) -> None
#
# Integration:
#   - Reads from Layer 1/2 (new messages, episodic memory)
#   - Written by state_updater.py at session end
#   - Queried by social_coaching.py and layer6_proactivity
#   - All transitions logged to Layer 12 audit trail
#
# State machine enforces valid transitions:
#   acquaintance → casual (mutual repeated interaction)
#   casual → close (disclosure, vulnerability, shared history)
#   close ↔ intimate (rare; requires deep vulnerability)
#   any → estranged (explicit user statement or multi-year silence)
