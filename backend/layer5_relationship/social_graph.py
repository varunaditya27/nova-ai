# Layer 5, Sub-Component: Social Graph Manager
#
# Responsibility: Maintain a structured, persistent model of every named person in the user's
# social world—built exclusively from what the user has said.
#
# The social graph is the substrate that makes all social intelligence possible.
# Without it, Layer 5 layers cannot reason about relational dynamics.
#
# Key data structures:
#   - SocialNode: One person (name, description, role in user's life, known attributes)
#   - SocialGraphEdge: Directed relationship (user → person, capturing user's perception)
#   - InteractionPattern: Recurring dynamics detected across multiple mentions
#   - Attribute: Facts about the person (occupation, personality trait, known location, etc.)
#
# Main functions:
#   - get_or_create_node(person_name, context) -> SocialNode
#   - add_attribute(node_id, attribute_type, value, confidence) -> None
#   - detect_pattern(node_id, pattern_description) -> InteractionPattern
#   - get_all_nodes() -> list[SocialNode]
#   - find_similar_relationships() -> list[RelationshipPair]  # for pattern recognition
#
# Integration:
#   - Reads from Layer 1/2 (new mentions in conversation, episodic memory)
#   - Updated by relationship_manager.py
#   - Queried by social_coaching.py and proactivity layer
#
# Design principle: No inference, no speculation. Only what the user has explicitly stated.
# Confidence scores reflect consistency of descriptions.
