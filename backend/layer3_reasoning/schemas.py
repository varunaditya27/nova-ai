# Schemas for Layer 3 — Emotion, Intent & Reasoning
#
# Defines emotion model, intent taxonomy, cognitive mode routing, and reasoning trace structures.
#
# Two-dimensional emotion model:
#   - valence: -1.0 (most negative) to +1.0 (most positive)
#   - arousal: 0.0 (calm) to 1.0 (maximally activated)
#
# Combined with discrete emotion taxonomy for human-readable interpretation:
#   High arousal + negative valence: anxiety, panic, anger
#   Low arousal + negative valence: sadness, despair, numbness
#   High arousal + positive valence: excitement, joy, elation
#   Low arousal + positive valence: contentment, calm satisfaction
#   Near-zero on both: neutral, flat affect, informational
#
# Key schemas:
#   - EmotionVector: (valence, arousal, dominant_label)
#   - CognitiveModeDecision: (mode: System1 | System2, rationale, risk_override)
#   - IntentClassification: (primary_intent, secondary_intents, is_tool_request, action_required)
#   - EmpathyHypothesis: (core_need, emotional_scaffolding, appropriate_response_stance)
#   - ReasoningTrace: (classification_signals, mode_decision_logic, final_intent)
#
# Design: All emotion/intent data is immutable after creation. TracedReasoning captures
# the full decision-making path for auditability and error analysis.
