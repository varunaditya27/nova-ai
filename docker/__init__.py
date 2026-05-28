# Docker Configuration & Containerization
#
# Containerized components:
#   1. Kokoro TTS: Docker container running TTS service on localhost:8880
#   2. Ollama: Optional Docker container for local LLM inference (or native install)
#   3. Backend: Optional Docker container for production deployment
#
# Files:
#   - Dockerfile: Backend container definition (if containerizing backend)
#   - docker-compose.yml: Multi-container orchestration (backend + Kokoro + Ollama)
#   - .env.example: Template for environment variables
#   - kokoro.Dockerfile: Kokoro TTS service definition
#   - ollama.Dockerfile: Ollama local LLM service definition
#
# Development:
#   - Run Kokoro in Docker for audio synthesis
#   - Run Ollama locally or in Docker for embeddings + System 1
#   - Backend runs locally during dev (Python venv)
#
# Production:
#   - All services containerized via docker-compose
#   - Environment-specific configs
