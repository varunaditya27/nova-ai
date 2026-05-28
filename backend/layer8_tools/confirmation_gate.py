# Layer 8, Sub-Component: Confirmation Gate
#
# Responsibility: Map tool action properties to confirmation tier (AUTO/SOFT/HARD).
#
# Tier definitions:
#   - AUTO: Low risk, easily reversible, safe to execute without asking (e.g., web search)
#   - SOFT: Medium risk or irreversible but non-damaging (e.g., create calendar event, draft email)
#   - HARD: High risk, costly, or sends external data (e.g., send email, delete file)
#
# Dimensions considered:
#   - tool_name: Some tools are inherently riskier
#   - action_type: create/read/update/delete; delete is riskier
#   - reversibility: Can the action be undone?
#   - external_impact: Does it affect systems outside Nova (email, calendar)?
#   - cost: Does it consume resources (API calls)?
#
# Main functions:
#   - compute_confirmation_tier(tool_name, action_type, parameters) -> ConfirmationTier
#   - get_confirmation_request(tool_name, action_summary) -> ConfirmationRequest
#
# Integration:
#   - Called by tool_manager before executing any tool
#   - Queries from config/layer8.yaml for tier mappings
#   - Returns ConfirmationRequest to be shown to user
#
# Design: Tier decisions are conservative. When in doubt, ask.
