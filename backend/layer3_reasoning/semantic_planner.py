# Layer 3, Sub-Component: Semantic Planner (Agent 4a)
#
# Responsibility: Generate the neutral, factually complete content of a response.
# This is what needs to be said, independent of emotional tone or phrasing.
#
# Called via infra.llm.groq_client (System 2 only; never System 1).
#
# Input:
#   - BuiltPrompt from Layer 4 (system prompt + context)
#   - User message
#   - EmpathyHypothesis (used to inform structure but not tone)
#
# Output:
#   - AgentDraft: Structured, content-complete draft response
#
# Main functions:
#   - generate_semantic_draft(prompt, user_message, empathy_hypothesis) -> AgentDraft
#   - stream_generation(same inputs) -> AsyncGenerator[str]
#
# Integration:
#   - Called only in System 2 path
#   - Output fed to emotion_refiner.py (Agent 4b) for tone refinement
#   - No modifications to prompt or context (read-only consumer)
#
# Architecture boundary: This component NEVER modifies the prompt or adds emotion.
# That is emotion_refiner's responsibility. Separation of concerns is strict.
