# Layer 3, Sub-Component: Two-Stage Pipeline Orchestrator
#
# Responsibility: Coordinate the full Layer 3 reasoning pipeline:
# empathy_hypothesis → semantic_planner → emotion_refiner
#
# This module does not perform reasoning itself. It orchestrates the sequence,
# handles error cases, applies timeouts, and ensures correct LLM routing.
#
# Main functions:
#   - run_full_layer3(user_message, context, emotion_vector) -> FinalReasoningOutput
#   - run_system1_fast_path(message, context, emotion) -> QuickResponse
#   - run_system2_full_path(message, context, emotion) -> FullReasoningOutput
#   - stream_reasoning(message, context, emotion) -> AsyncGenerator[Event]
#
# Integration:
#   - Entry point called by conversation_orchestrator.py
#   - Calls cognitive_mode_arbiter for routing decision
#   - Orchestrates LLM calls via semantic_planner and emotion_refiner
#   - Handles streaming or full generation based on session preference
#   - Passes result to Layer 4 (Persona)
#
# Design principle: Zero business logic; pure orchestration of sub-components.
