# Ollama Client
#
# Responsibility: Wrapper around local Ollama API (httpx).
#
# Usage:
#   - System 1 fast responses (quick chat)
#   - Classifiers (emotion, intent, crisis detection)
#   - Any fast inference that doesn't need reasoning
#
# Models (run locally):
#   - qwen2.5:7b (System 1 fast responses)
#   - gemma3:4b (classifiers)
#   - nomic-embed-text (embeddings)
#
# Main functions:
#   - complete(prompt, model, temperature, max_tokens, ...) -> str
#   - stream(prompt, model, temperature, max_tokens, ...) -> AsyncGenerator[str]
#
# Configuration:
#   - OLLAMA_URL: Ollama endpoint (default: http://localhost:11434)
#   - Models read from config/layer3.yaml (which models to use for which tasks)
