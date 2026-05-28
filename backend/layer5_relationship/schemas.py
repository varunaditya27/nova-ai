# Schemas for Layer 5 — Social Intelligence & Coaching
#
# Defines relationship structures, social graph, and coaching opportunity detection.
#
# Key schemas:
#   - RelationshipState: Full record of a relationship the user has described
#     (person_id, stage, tie_strength, interaction_frequency, conflict_history, etc.)
#   - RelationshipStage: Enum (acquaintance, casual, close, intimate, estranged, conflicted)
#   - TieStrength: 0.0–1.0 score representing relationship depth and closeness
#   - SocialNode: A person in the user's social graph
#   - SocialGraphEdge: Relationship between two nodes (directed: how user perceives them)
#   - InteractionPattern: Recurring dynamic (e.g., "they withdraw when criticized", "we have inside jokes")
#   - CoachingOpportunity: Detected situation where social advice would be valuable
#   - SocialMilestone: Relationship event (met them, had conflict, reconnected, etc.)
#   - DisclosureLogEntry: When/how/what the user disclosed to this person
#
# Design: Social graph is built purely from what the user has said (no inference/speculation).
# Confidence scores reflect consistency of descriptions. Relationships evolve through
# explicit stage transitions, not automatic score changes.
