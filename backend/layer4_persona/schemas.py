# Schemas for Layer 4 — Persona, Personality & Response Generation
#
# Defines personality vector, persona state, and prompt builder structures.
#
# PersonalityVector: A learned representation of Nova's identity in this session.
# Not static. Evolves based on interaction patterns, but slowly and conservatively.
#
# Structure:
#   - name, pronouns (stable)
#   - core_values: list[Belief] with centrality scores and confidence
#   - communication_style: dimension vector (formal←→casual, direct←→indirect, verbose←→terse)
#   - emotional_baseline: learned from prior sessions
#   - personality_traits: Big Five or similar taxonomy with scores and confidence
#   - adaptation_history: Recent drift vectors and their justifications
#
# PersonaState: Current persona snapshot for this session (read at session start from memory).
#
# BuiltPrompt: The assembled system prompt, context block, and response constraints.
#   - system_prompt: str (the actual LLM system prompt)
#   - context_block: str (retrieved memories, relationship state, goals, etc.)
#   - constraints: list[ResponseConstraint] (things Nova must/must-not do)
#   - length_target: (short/medium/long based on circadian + mood)
#   - mode: (casual_chat, task_help, emotional_support, crisis_support)
#
# Design: All structures immutable after creation. Updates go through State Updater.
