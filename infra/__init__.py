# Infrastructure Layer — Plumbing
#
# This directory contains everything that is NOT a cognitive layer.
# Pure integrations, wrappers, and system infrastructure.
#
# Core principle: No business logic here. Only implementations of interfaces.
# Cognitive layers never import from infra directly; dependencies are injected by pipeline or FastAPI.
#
# Main components:
#   - db/: Postgres via SQLAlchemy (engine, base, models); SQLite backs the offline test suite
#   - vector_store/: ChromaDB (client, collections, embeddings)
#   - llm/: LLM clients (base interface, Ollama wrapper) — fully offline, no cloud provider
