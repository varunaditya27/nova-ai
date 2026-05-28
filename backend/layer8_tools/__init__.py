# Layer 8 — Tool Use & Actions
#
# Responsibility: When the user asks Nova to DO something (not just think/respond),
# this layer orchestrates the action: intent detection → confirmation → execution → recording.
#
# Tool categories:
#   - Calendar integration (Google, Apple, Outlook)
#   - Email (draft and send)
#   - Web search
#   - Note-taking (Notion, Obsidian, markdown files)
#   - Reminders
#   - Future: SMS, payments, etc.
#
# Core principle: High-risk actions require explicit user confirmation.
# Low-risk actions may auto-execute. All actions are recorded and auditable.
#
# Main components:
#   - tool_manager.py: Orchestrates intent → confirm → execute → record
#   - confirmation_gate.py: Maps (risk_level, reversibility) → confirm tier
#   - parameter_resolver.py: Detects missing params; single-question prompting
#   - action_recorder.py: Writes ActionRecord; links to episodic memory
#   - base_plugin.py: Abstract interface all tools implement
#   - plugins/: Calendar, Email, WebSearch, Notes, Reminders implementations
#   - schemas.py: ActionRecord, ConfirmationRequest, ToolIntent, ParameterGap
#
# Contract: Tool outputs are advisory. User always has final say.
