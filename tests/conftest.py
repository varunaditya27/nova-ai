# Shared Test Fixtures & Configuration
#
# Provides:
#   - db_session: In-memory SQLite session (pytest fixture)
#   - mock_groq_client: Mock Groq API client
#   - mock_ollama_client: Mock Ollama API client
#   - mock_chroma_client: Mock ChromaDB instance
#   - session_cache: Ephemeral session cache
#   - test_user: Pre-created test user
#   - sample_memories: Pre-populated episodic/semantic memories
#
# Scope: session/function (per fixture requirements)
#
# Isolation: Each test gets fresh DB session (rollback at end)
