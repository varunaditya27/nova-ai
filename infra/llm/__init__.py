# LLM Clients
#
# Swappable LLM backends. All implement the same interface.
#
# Components:
#   - base_client.py: Abstract LLMClient interface
#   - groq_client.py: Groq API wrapper (System 2, reasoning)
#   - ollama_client.py: Ollama local wrapper (System 1, classifiers)
#
# Core principle: Cognitive layers never import llm clients directly.
# Dependencies are injected by pipeline or FastAPI.
