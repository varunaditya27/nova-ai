# FastAPI Dependencies
#
# Responsibility: Provide dependency injection for endpoints.
#
# Main dependencies:
#   - get_db() -> Generator[Session, None, None]: SQLite session
#   - get_current_user() -> User: Current authenticated user
#   - get_groq_client() -> GroqClient: Groq API wrapper
#   - get_ollama_client() -> OllamaClient: Ollama API wrapper
#   - get_chroma_client() -> PersistentClient: ChromaDB client
#   - get_memory_store() -> MemoryStore: Memory store interface
#   - get_session_cache() -> SessionCache: Current turn's session cache
#
# All injected at endpoint level via FastAPI's Depends()
