# Layer 4 — Persona, Personality & Response Generation
#
# Core question: Who is responding and how?
#
# This layer is where all upstream signals converge into an actual response:
# language, tone, content, structure, phrasing, and personality expression.
#
# Central distinction: Layer 4 builds the governing constraints (the persona/personality).
# Layer 3 generates the content within those constraints.
# They never mix.
#
# Architecture: Three sequential sub-systems:
#   1. Persona Engine: Defines Nova's stable identity and constrains how it can respond
#   2. Semantic Planner (Agent 4a): Generates factual, task-complete content
#   3. Emotion Refiner (Agent 4b): Transforms content into emotionally appropriate language
#
# NOTE: Layer 3 AND Layer 4 both contain semantic_planner and emotion_refiner modules.
# Confusing but correct per the architecture docs. Layer 3 orchestrates the reasoning.
# Layer 4 orchestrates the persona/constraint building.
#
# Main components:
#   - personality_vector.py: PersonalityVector schema + update logic
#   - drift_controller.py: Centrality-weighted drift gate (prevents over-adaptation)
#   - prompt_builder.py: Assembles final system prompt from vector + context
#   - schemas.py: PersonalityVector, PersonaState, BuiltPrompt
#
# Contract: Produces immutable BuiltPrompt consumed by Layer 3/4's LLM agents.
