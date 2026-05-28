# Layer 8, Sub-Component: Parameter Resolver
#
# Responsibility: Detect missing parameters and resolve them with minimal user friction.
#
# When a tool intent is detected but parameters are incomplete:
#   - Identify which parameter is missing
#   - Generate a single, natural clarifying question
#   - Wait for user response
#   - Re-invoke tool with complete parameters
#
# Principle: One question per turn. Never bombard with multiple gaps.
# If more than one parameter is missing, prioritize: ask for the most critical first.
#
# Main functions:
#   - detect_parameter_gaps(tool_intent: ToolIntent) -> list[ParameterGap]
#   - generate_clarification_question(gap: ParameterGap) -> str
#   - resolve_parameter(gap: ParameterGap, user_response: str) -> ParameterValue
#
# Integration:
#   - Called by tool_manager before confirmation gate
#   - May loop back to Layer 9 to ask the clarifying question
#   - Called again on next user message with the response
#
# Design: Parameter resolution is conversational, not form-like.
