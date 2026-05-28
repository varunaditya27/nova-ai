# Layer 5, Sub-Component: Social Coaching
#
# Responsibility: Detect coaching opportunities and generate socially-aware advice.
#
# This is where Nova goes beyond response generation and offers genuine social perspective.
# Examples:
#   - "You've mentioned this conflict three times now. Have you considered...?"
#   - "This sounds like the same dynamic you described with your roommate."
#   - "They might be struggling too. Here's another perspective..."
#
# Main functions:
#   - detect_coaching_opportunity(user_message, context) -> CoachingOpportunity | None
#   - generate_coaching_response(opportunity, relationship_context) -> CoachingResponse
#   - should_offer_coaching(user_id) -> bool  # frequency gate
#   - get_relevant_prior_patterns(current_situation) -> list[RelationshipPattern]
#
# Integration:
#   - Runs in parallel with Layer 4 when conversation domain is "relationships" or "social"
#   - Runs post-response for other domains (background processing)
#   - SC-4/SC-5 only inject into response if opportunity is detected AND timing is right
#   - Integrates advice into Layer 4 response via response_modifier
#
# Design: Coaching is offered, not imposed. User can always dismiss or ignore.
# It is grounded in user's own prior statements, not generic advice.
