# Layer 13, Sub-Component: Context Constructor
#
# Responsibility: Accelerate context building during first session(s).
#
# Unlike normal operation, where context is accumulated over weeks:
#   - Cold start infers rapidly from first few messages
#   - Builds basic personality vector from language analysis
#   - Initializes User World Model
#   - Detects key relationships and topics
#   - Establishes emotional baseline
#
# Main functions:
#   - construct_initial_context(first_messages) -> InitialContext
#   - build_personality_seeds(message_samples) -> PersonalityVectorSeeds
#   - establish_emotional_baseline(messages) -> EmotionalBaseline
#   - initialize_user_world_model(context) -> UserWorldModel
#
# Integration:
#   - Runs during cold start after first 2-3 messages
#   - Calls passive_elicitation for signal extraction
#   - Builds lightweight personality vector (not full vector—lightweight)
#   - Used by prompt_builder for first responses
#
# Design: Quick initialization. Lightweight. Refined over time as system learns more.
