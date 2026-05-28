# Schemas for Layer 8 — Tool Use & Actions
#
# Defines tool intents, confirmations, actions, and plugin interfaces.
#
# Key schemas:
#   - ToolIntent: Parsed user intent to use a tool
#     (tool_name, action_type, parameters_present, parameters_missing, confidence)
#   - ConfirmationRequest: Request for user confirmation before executing
#     (request_id, tool_name, action_description, risk_level, confirmation_type)
#   - ConfirmationTier: Enum (AUTO, SOFT, HARD)
#   - ActionRecord: Log of a tool execution
#     (action_id, tool_name, action_type, parameters, outcome, timestamp, user_session_id)
#   - ParameterGap: Missing parameter that needs to be resolved
#   - ToolPlugin: Abstract interface for all plugins
#
# Design: All tool operations are auditable and reversible (where possible).
# User can inspect what Nova did via Layer 12 (Privacy) memory audit.
