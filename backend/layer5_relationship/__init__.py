# Layer 5 — Social Intelligence & Coaching
#
# Core question: What does Nova understand about the people in the user's life
# and the social dynamics between them?
#
# This layer operates at a longer timescale—accumulating social knowledge across sessions.
# It builds a model of the user's relational world and provides coaching, perspective,
# and pattern recognition that users cannot always give themselves.
#
# Central distinction: Layer 3 reads emotional state of current message.
# Layer 4 crafts emotionally appropriate response.
# Layer 5 operates across sessions and offers social perspective.
#
# NOT a therapy layer. NOT a crisis layer. It's social intelligence—like a trusted friend
# who has been paying close attention to your relationships and can notice patterns.
#
# Main components:
#   - relationship_manager.py: RelationshipState CRUD + stage transition state machine
#   - tie_strength_calculator.py: Computes tie strength score from interaction signals
#   - social_graph.py: Named people in user's life + relationship dynamics
#   - self_disclosure_engine.py: Disclosure gating by stage + trajectory tracking
#   - social_coaching.py: Advice calibrated to relationship history + stage
#   - schemas.py: RelationshipState, RelationshipStage, TieStrength, SocialNode
#
# Contract: SC-1 through SC-3 always updating. SC-4 and SC-5 only inject into active response
# when coaching opportunity is detected and timing conditions are met.
