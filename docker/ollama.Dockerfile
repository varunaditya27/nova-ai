# Ollama Docker Container
#
# Purpose: Run local LLM models for System 1 + embeddings
#
# Image: ollama/ollama:latest
# Port: 11434
# Protocol: Ollama REST API
#
# Models (auto-pulled on first request):
#   - qwen2.5:7b: System 1 fast classifier (< 2s)
#   - gemma3:4b: System 1 fallback / embedding alternative
#   - nomic-embed-text: Semantic embeddings for memory recall
#
# Configuration:
#   - OLLAMA_HOST: API bind address (default: 0.0.0.0:11434)
#   - OLLAMA_MODELS: Base directory for models (default: ~/.ollama/models)
#
# Build:
#   No custom build needed; use ollama/ollama:latest
#
# Run (standalone):
#   docker run -d -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
#
# Integration:
#   Used by Layer 3 (cognitive_mode_arbiter, two_stage_pipeline)
#   Connected via docker-compose or localhost:11434
#
# Model Management:
#   ollama pull qwen2.5:7b
#   ollama pull gemma3:4b
#   ollama pull nomic-embed-text
