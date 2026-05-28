# Layer 3, Sub-Component: Emotion Refiner (Agent 4b)
#
# Responsibility: Take the semantic draft from Agent 4a and rewrite it to match the emotional moment.
#
# This component adjusts:
#   - Tone and register (formal → casual, clinical → warm)
#   - Sentence structure (complex → simple, short → long)
#   - Phrasing and word choice (precise → empathetic, detached → present)
#   - Micro-interactions (backchannels, thinking pauses, self-edits)
#
# Input:
#   - AgentDraft from semantic_planner.py
#   - EmpathyHypothesis (core need, emotional scaffolding, stance)
#   - BuiltPrompt from Layer 4
#
# Output:
#   - Refined AgentDraft: Same content, emotionally appropriate tone
#
# Main functions:
#   - refine_with_emotion(semantic_draft, empathy_hypothesis, prompt) -> AgentDraft
#   - stream_refinement(same inputs) -> AsyncGenerator[str]
#   - skip_refinement_decision(context) -> bool
#
# Integration:
#   - Called only in System 2 path, after semantic_planner completes
#   - Called via infra.llm.groq_client
#   - Output fed to Layer 9 (Output Delivery)
#   - May be skipped (per Layer 3 decision) for performance
