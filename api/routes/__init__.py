# API Routes
#
# Endpoint definitions organized by domain.
#
# Routes:
#   - chat.py: WS /chat/stream, POST /chat (primary conversation endpoint)
#   - memory.py: GET /memory/audit, GET /memory/{id}, PATCH /memory/{id}, DELETE /memory/{id}
#   - goals.py: GET/POST /goals, GET/PATCH/DELETE /goals/{id}, GET/POST /goals/{id}/tasks
#   - tools.py: GET /tools/pending, POST /tools/confirm/{id}
#   - sync.py: POST /sync/push, GET /sync/pull (cross-device sync)
#   - auth.py: POST /auth/register, POST /auth/login, POST /auth/refresh (auth)
