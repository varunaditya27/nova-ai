# Layer 3, Sub-Component: Empathy Hypothesis Generator
#
# Responsibility: Construct a structured empathy hypothesis from emotional signals and context.
#
# The hypothesis answers: "What is the user's core need right now? What emotional scaffolding
# would make a response feel appropriate and caring rather than clinical or dismissive?"
#
# Outputs EmpathyHypothesis with:
#   - core_need: What does this person need from me right now? (validation, solution, presence, etc.)
#   - emotional_scaffolding: How should the response be emotionally framed?
#   - appropriate_stance: Am I being warm/empathetic, neutral/analytical, celebratory, etc.?
#   - key_emotional_keywords: Words/themes that should appear in response
#   - things_to_avoid: Topics/frames that would feel tone-deaf
#
# Main functions:
#   - generate_hypothesis(emotion_vector, context, prior_memory) -> EmpathyHypothesis
#
# Integration:
#   - Reads from Layer 2 (recent emotional history, relationship stage)
#   - Reads from Layer 1 (circadian band, session gap)
#   - Output consumed by emotion_refiner.py (Agent 4b)
#   - No LLM calls (deterministic rule-based or learned heuristic)
