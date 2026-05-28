# Layer 11, Sub-Component: Escalation Engine
#
# Responsibility: Manage when and how to surface professional resources and emergency contacts.
#
# Tier structure:
#   - Tier 0: MONITORING — No outward change; system becomes attentive
#   - Tier 1: ELEVATED — Gentle care escalation; no resource surfacing yet
#   - Tier 2: CRISIS — Resources offered; 988 Suicide & Crisis Lifeline (US), local equivalents
#   - Tier 3: IMMINENT — Emergency response; 911 / emergency contact
#
# Main functions:
#   - escalate_to_tier(current_tier, new_level) -> EscalationTier
#   - get_resources_for_tier(tier: EscalationTier, location, language) -> list[Resource]
#   - compose_escalation_message(tier, context) -> str
#   - trigger_emergency_contact(user_id) -> bool  [Tier 3 only]
#
# Integration:
#   - Called by safety_agent when escalation is warranted
#   - Produces crisis response (overrides normal response)
#   - Logs all escalations with timestamp, signals, and rationale
#   - Integrates with Layer 12 audit trail
#
# Design: Escalation is gradual, not abrupt. User is never abandoned.
# Tier transitions happen when evidence warrants, not automatically.
