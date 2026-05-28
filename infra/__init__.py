# Infrastructure Layer — Plumbing
#
# This directory contains everything that is NOT a cognitive layer.
# Pure integrations, wrappers, and system infrastructure.
#
# Core principle: No business logic here. Only implementations of interfaces.
# Cognitive layers never import from infra directly; dependencies are injected by pipeline or FastAPI.
#
# Main components:
#   - session_cache.py: In-process working memory buffer for current turn
#   - db/: SQLite via SQLAlchemy (engine, base, models, migrations)
#   - vector_store/: ChromaDB local persistent (client, collections, embeddings)
#   - llm/: LLM clients (base interface, Groq wrapper, Ollama wrapper)
#   - websocket/: Real-time delivery to frontend (connection manager, event emitter)
