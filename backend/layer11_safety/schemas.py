# Schemas for Layer 11 — Safety & Crisis Architecture
#
# Defines crisis signals, escalation tiers, and safety records.
#
# Five Crisis Levels:
#   - NONE: No crisis signals; normal conversation
#   - MONITORING: Low-weight signals (vague hopelessness, minor self-harm language); system becomes more careful
#   - ELEVATED: Multiple low-weight or one high-weight signal; conversation mode switches to crisis_support
#   - CRISIS: Explicit intent or high-risk behavior; maximum response, resources surfaced
#   - IMMINENT: Immediate danger signals; emergency protocol, max response
#
# Key schemas:
#   - CrisisSignal: Detected signal (type, weight, rationale, timestamp)
#   - CrisisLevel: Enum (NONE, MONITORING, ELEVATED, CRISIS, IMMINENT)
#   - EscalationTier: Enum (Tier0, Tier1, Tier2, Tier3)
#   - SafetyRecord: Log of all crisis signals and escalations
#   - SafeModeState: Current state (active, escalation_level, resources_offered)
#
# Design: Crisis detection is sensitive (high recall) at controlled false-positive rate.
