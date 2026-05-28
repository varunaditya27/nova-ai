# Layer 8, Sub-Component: Action Recorder
#
# Responsibility: Record all tool executions in an auditable log and link to episodic memory.
#
# Every tool action produces an ActionRecord with:
#   - action_id, timestamp, tool_name, action_type, parameters
#   - outcome (success/failure), result_summary, error_message (if failed)
#   - user_session_id, user_id
#   - linked_episodic_memory_id (for retrieval context)
#
# Main functions:
#   - record_action(action: ActionRecord) -> action_id
#   - record_action_outcome(action_id, outcome, result) -> None
#   - link_to_episodic_memory(action_id, memory_id) -> None
#   - get_action_history(user_id, tool_name=None) -> list[ActionRecord]
#
# Integration:
#   - Called after every tool execution by tool_manager
#   - Records go to infra.db.models.tools.ActionRecord
#   - Auditable via Layer 12 (Privacy) memory audit interface
#   - Used by Layer 10 (Longitudinal) for action history in life narrative
#
# Design: No action is hidden. Everything is recorded and user-inspectable.
