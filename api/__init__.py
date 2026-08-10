# FastAPI Application
#
# HTTP surface for the Nova AI backend (WebSocket transport is a documented follow-up; SSE is live).
#
# Main components:
#   - main.py: App factory, router mounting, dependency injection, lifespan events
#   - dependencies.py: FastAPI dependency injection (state, tool_manager, etc.)
#   - routes/: Endpoint definitions — see docs/API_REFERENCE.md for the full 40+ route surface
#   - middleware/: Request/response interceptors (logging.py)
#   - assembly.py: wires every PipelineSteps hook onto real layer entrypoints
#   - streaming.py: SSE token pacing for /chat/stream
