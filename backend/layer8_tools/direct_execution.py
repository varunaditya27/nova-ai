"""SC-1 direct execution path — fail-closed on gated tiers (architecture doc §5.1).

Split out of ``tool_manager.py``: ``ToolManager.execute_tool`` bypasses the ``process()``
per-message flow (e.g. a client re-submitting a confirmed action directly), so it must
independently re-check the confirmation gate rather than trusting the caller.
"""

from __future__ import annotations

from backend.layer8_tools import confirmation_gate
from backend.layer8_tools.pending_confirmation import fingerprint as _fingerprint
from backend.layer8_tools.schemas import ToolOutcome, ToolResult


def consume_token(manager, confirmation_id, tool_name, operation, parameters, user_id) -> bool:
    """Validate + single-use-consume a confirmation token bound to this exact action."""
    if not confirmation_id:
        return False
    pending = manager._pending.get(confirmation_id)
    if pending is None:
        return False
    if pending.fingerprint != _fingerprint(tool_name, operation, parameters, user_id):
        return False                                       # bound to a different action/user
    del manager._pending[confirmation_id]                  # consume (anti-replay)
    return True


def execute_tool_direct(
    manager, tool_name: str, operation: str, parameters: dict,
    user_id=None, session_id=None, action_type=None, confirmation_id=None,
) -> ToolResult:
    plugin = manager.get_plugin(tool_name)
    if plugin is None or not plugin.supports(operation):
        return ToolResult(tool_name, operation, ToolOutcome.FAILURE.value,
                          error_message=f"no plugin for {tool_name}.{operation}")
    cap = plugin.capability_for(operation)

    # Authorization first: a gated op needs a valid, matching, unconsumed token.
    if confirmation_gate.requires_user_confirmation(manager._tier_for(cap)):
        if not consume_token(manager, confirmation_id, tool_name, operation, parameters, user_id):
            result = ToolResult(tool_name, operation, ToolOutcome.FAILURE.value,
                                error_message="confirmation required for this action")
            manager.recorder.record_from_result(
                result, action_type=cap.action_type, parameters=parameters,
                user_id=user_id, user_session_id=session_id)
            return result

    validation = plugin.validate_parameters(operation, parameters)
    if not validation.valid:
        result = ToolResult(tool_name, operation, ToolOutcome.FAILURE.value,
                            error_message="; ".join(validation.errors))
        manager.recorder.record_from_result(
            result, action_type=cap.action_type, parameters=parameters,
            user_id=user_id, user_session_id=session_id)
        return result

    result, _ = manager._execute_and_record(
        plugin, operation, parameters, action_type or cap.action_type, user_id, session_id)
    return result
