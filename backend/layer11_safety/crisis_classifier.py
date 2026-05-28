# Layer 11, Sub-Component: Crisis Classifier
#
# Responsibility: Real-time, multi-signal detection of crisis indicators per message.
#
# Signals detected:
#   - Text patterns: Self-harm language, suicidal ideation, abuse, hopelessness
#   - Temporal patterns: Atypical message timing (3 AM after weeks of silence)
#   - Emotional intensity: Sudden shift to high distress after stable baseline
#   - Prior history: Known vulnerabilities, prior crisis episodes
#   - Behavioral change: Abrupt messaging frequency change, language shift
#
# Main functions:
#   - classify_message(user_message, context, crisis_history) -> list[CrisisSignal]
#   - compute_crisis_level(signals: list[CrisisSignal]) -> CrisisLevel
#   - should_escalate(current_level, new_signals) -> bool
#
# Integration:
#   - Called by safety_agent on every message
#   - Runs in parallel (does not block main pipeline)
#   - May call LLM for nuanced pattern detection
#   - Output passed to escalation_engine
#
# Design: Conservative approach—when in doubt, flag it.
# False positives are preferable to missed crises.
