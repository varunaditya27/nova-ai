# Layer 8 Tool Plugins
#
# Each plugin implements the ToolPlugin interface (execute, undo, capabilities). The
# intent -> resolve -> confirm -> execute -> audit pipeline around them is real and fully tested.
#
# Current status: all five plugins (calendar_plugin.py, email_plugin.py, web_search_plugin.py,
# notes_plugin.py, reminders_plugin.py) run against local, in-memory backends by design — no
# external service (Google Calendar, SMTP, a real search API, ...) is wired in, and plugin state
# doesn't survive a restart. This proves the architecture end-to-end as a deliberate
# proof-of-concept scope, not a bug. See docs/POLISH_BACKLOG.md before wiring a real backend in.
