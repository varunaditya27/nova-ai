# Layer 8 Tool Plugins
#
# Each plugin implements the ToolPlugin interface and integrates with an external service.
# Plugins are swappable—the same interface, different backends.
#
# Implemented plugins:
#   - calendar_plugin.py: Google Calendar / Apple Calendar / Outlook integration
#   - email_plugin.py: Draft and send emails (careful: high confirmation tier)
#   - web_search_plugin.py: Search, filter, extract, synthesize
#   - notes_plugin.py: Capture to Notion / Obsidian / markdown files
#   - reminders_plugin.py: Create and retrieve reminders
#
# Not implemented (stubs in backend/_stubs/):
#   - sms_plugin.py
#   - payments_plugin.py
#   - habit_tracker_plugin.py
#
# All plugins adhere to:
#   - execute(parameters) -> ToolResult
#   - undo() -> bool (if reversible)
#   - capabilities() -> list[str]
#   - validate_parameters(parameters) -> ValidationResult
