# Groq Client
#
# Responsibility: Wrapper around Groq API (async-groq library).
#
# Usage:
#   - System 2 reasoning (complex, emotional, goals)
#   - Semantic planner (Agent 4a)
#   - Emotion refiner (Agent 4b)
#
# Model:
#   - llama-3.3-70b-versatile (free tier, powerful reasoning)
#
# Main functions:
#   - complete(prompt, temperature, max_tokens, ...) -> str
#   - stream(prompt, temperature, max_tokens, ...) -> AsyncGenerator[str]
#
# Configuration:
#   - GROQ_API_KEY: API key (from environment)
#   - GROQ_MODEL: Model name (configurable)
