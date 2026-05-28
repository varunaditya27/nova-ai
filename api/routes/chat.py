# Chat Routes
#
# Responsibility: Primary conversation endpoint.
#
# Endpoints:
#   - WS /chat/stream (primary): WebSocket streaming of response events
#   - POST /chat: Fallback sync endpoint (for non-WebSocket clients)
#
# Workflow:
#   1. Accept user message
#   2. Call pipeline/conversation_orchestrator
#   3. Stream events to client (thinking, typing, audio, etc.)
#   4. Trigger state_updater post-turn (async, non-blocking)
#
# Authentication: Bearer token required (from /auth/login)
