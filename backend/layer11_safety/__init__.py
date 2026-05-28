# Layer 11 — Safety & Crisis Architecture
#
# Core principle: More human-like Nova is more dangerous without robust safety architecture.
# This layer exists to ensure capability does not cause harm.
#
# Layer 11 is NOT optional. It determines whether Nova is good for people.
#
# The architecture operates at different timescales addressing different risks:
#   - SC-1: Ethical Guardrails — ambient protection against manipulation
#   - SC-2: Crisis Detection — real-time identification of psychological danger
#   - SC-3: Escalation Protocol — structured response once crisis is detected
#   - SC-4: Dependency Monitor — longitudinal detection of unhealthy reliance
#
# Governing principle: Protective action must never feel punitive, clinical, or interrupting.
# Safety systems that make users feel judged or abandoned defeat their own purpose.
#
# Main components:
#   - safety_agent.py: Entry point (runs FIRST on every turn)
#   - crisis_classifier.py: Multi-signal detection of crisis indicators
#   - escalation_engine.py: Tier 1 → Tier 2 → Tier 3 protocol
#   - safe_mode_enforcer.py: Hard override—suppresses micro-interactions, plain prose
#   - schemas.py: CrisisSignal, EscalationTier, SafetyRecord, SafeModeState
#
# Execution model: Safety agent runs BEFORE Layer 1 on every single turn.
# It has veto authority over the normal response pipeline.
