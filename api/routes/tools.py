# Tools Routes
#
# Responsibility: Tool confirmation and management.
#
# Endpoints:
#   - GET /tools/pending: List pending confirmations awaiting user response
#   - POST /tools/confirm/{id}: Confirm (approve) a pending tool action
#   - POST /tools/deny/{id}: Deny a pending tool action
#   - GET /tools/history: Tool execution history
#
# All operations go through Layer 8 tool_manager.
