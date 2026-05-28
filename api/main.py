# FastAPI Application Factory
#
# Responsibility: Create and configure the FastAPI app instance.
#
# Performs:
#   1. Create app instance
#   2. Register all routers (chat, memory, goals, etc.)
#   3. Register middleware (logging, error handlers)
#   4. Configure lifespan events (startup, shutdown)
#   5. Set up dependency injection
#   6. Configure CORS (for NextJS frontend on localhost:3000)
#
# Main function:
#   - create_app() -> FastAPI
#
# Lifespan events:
#   - on_startup(): Initialize LLM clients, DB, vector store, scheduler
#   - on_shutdown(): Clean up connections, gracefully shut down background jobs
