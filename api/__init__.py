# FastAPI Application
#
# HTTP + WebSocket surface for the Nova AI backend.
#
# Main components:
#   - main.py: App factory, router mounting, dependency injection, lifespan events
#   - dependencies.py: FastAPI dependency injection (db_session, current_user, llm_client, etc.)
#   - routes/: Endpoint definitions (chat, memory, goals, tools, sync, auth)
#   - middleware/: Request/response interceptors (logging, error handling, etc.)
