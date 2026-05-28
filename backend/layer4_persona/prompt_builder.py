# Layer 4, Sub-Component: Prompt Builder
#
# Responsibility: Assemble the final system prompt from personality vector, context, and constraints.
#
# This is where all the scattered data comes together into the instruction set that
# governs the upcoming LLM call. The resulting BuiltPrompt is immutable and passed
# directly to semantic_planner (Agent 4a) for generation.
#
# Main functions:
#   - build_prompt(personality_vector, context, user_message, mode) -> BuiltPrompt
#   - build_system_prompt() -> str
#   - build_context_block(memories, relationship_state, goals, proactive_items) -> str
#   - build_constraints(safety_state, mode, user_preferences) -> list[ResponseConstraint]
#
# Integration:
#   - Called by conversation_orchestrator at the start of Layer 4 processing
#   - Reads from Layer 2 (personality vector, recalled memories)
#   - Reads from Layer 5 (relationship state)
#   - Reads from Layer 7 (active goals)
#   - Reads from Layer 8 (crisis state, safety flags)
#   - Passes immutable BuiltPrompt to Layer 3's semantic_planner
#
# Design principle: Separation of concerns is absolute.
# This layer builds what to be constrained by. Layer 3 builds what to say within those constraints.
