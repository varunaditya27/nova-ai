# Layer 9, Sub-Component: Length Calibrator
#
# Responsibility: Compute appropriate response length based on context.
#
# Length targets (approximate tokens):
#   - short: 40 (curt, single point)
#   - medium: 80 (typical response)
#   - long: 220 (detailed, multi-point)
#
# Factors:
#   - Circadian band: Late night → shorter (user may be tired)
#   - Emotional intensity: High emotion → longer (more support needed)
#   - Conversation history: If user's last message was short → respond shorter
#   - User preference: Learned from engagement signals (Layer 9 format profile)
#   - Domain: Task help → medium/long; casual chat → medium/short
#
# Main functions:
#   - compute_length_target(context) -> LengthTarget
#   - learned_user_length_preference(user_id) -> LengthTarget
#
# Integration:
#   - Called by Layer 4 (prompt_builder) before generating response
#   - Read by Layer 3 (semantic_planner) to constrain generation
#   - Updated by user_format_profile based on engagement signals
#
# Design: Length target is advisory to LLM, not a hard constraint.
# Gives generator guidance but allows overrides for good reasons.
