# WebSocket Connection Manager
#
# Responsibility: Registry of active WebSocket connections and session lifecycle.
#
# Main functions:
#   - connect(websocket, user_id, session_id) -> None
#   - disconnect(websocket, user_id) -> None
#   - broadcast(user_id, message) -> None
#   - get_active_sessions(user_id) -> list[SessionID]
#
# Design:
#   - One connection per user session
#   - Multiple connections if user has multiple browser tabs open
#   - Messages broadcast to all active connections
