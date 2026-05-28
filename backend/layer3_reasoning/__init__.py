# Layer 3 — Emotion, Intent & Reasoning
#
# Core question: What is actually happening emotionally and cognitively right now?
#
# This is the interpretive core of the pipeline. It reads meaning—not just text.
# Every upstream signal (circadian prior, implicit signals, recalled memories, User World Model)
# converges here and is synthesized into a structured understanding of the current moment.
#
# Central claim: Emotional context is the primary signal that determines response appropriateness.
# Getting the emotion right and content wrong is recoverable.
# Getting content right and emotion wrong is not.
#
# Architecture: Two functional groups:
#   1. Classification Group: Emotion Classifier, Background State Tracker, Intent Classifier, Mismatch Detector
#   2. Reasoning Group: Empathy Hypothesis Generator, Conversation Mode Resolver
#
# Output: EmotionIntentPacket (read-only) consumed by all response-generation layers.
#
# Main components:
#   - cognitive_mode_arbiter.py: System 1/2 routing (calls Ollama gemma3:4b)
#   - empathy_hypothesis.py: Builds EmpathyHypothesis from emotional signals
#   - semantic_planner.py: Agent 4a—neutral factual draft via Groq
#   - emotion_refiner.py: Agent 4b—empathy-shaped rewrite via Groq
#   - two_stage_pipeline.py: Orchestrates empathy_hypothesis → 4a → 4b
#   - schemas.py: CognitiveModeDecision, EmpathyHypothesis, ReasoningTrace
#
# Contract: Produces read-only EmotionIntentPacket; never modifies upstream data.
