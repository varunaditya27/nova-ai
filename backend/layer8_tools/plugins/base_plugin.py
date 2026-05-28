# Base Plugin Interface
#
# Abstract base class that all plugins implement.
# Enforces consistent interface across all tool integrations.
#
# Key methods:
#   - execute(parameters: dict) -> ToolResult: Perform the action
#   - undo() -> bool: Reverse the action (if reversible); return whether undo was successful
#   - capabilities() -> list[Capability]: List what this plugin can do
#   - validate_parameters(parameters: dict) -> ValidationResult: Check params are valid
#   - authenticate() -> bool: Set up credentials (called at startup)
#   - is_healthy() -> bool: Health check for this plugin
#
# Every plugin subclass must implement all methods or explicitly state why (abstract).
# This ensures tool_manager has a uniform interface across all integrations.
