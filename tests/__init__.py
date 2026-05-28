# Test Suite
#
# Tests mirror source exactly — one test file per logic file.
# (No tests for __init__.py or schemas.py files)
#
# Organization:
#   - tests/conftest.py: Shared fixtures (in-memory SQLite, mock LLMs, mock ChromaDB, etc.)
#   - tests/unit/: Layer-specific unit tests (one per layer file with logic)
#   - tests/integration/: End-to-end pipeline tests
#
# Key fixtures:
#   - db_session: In-memory SQLite session
#   - mock_groq_client: Mock Groq responses
#   - mock_ollama_client: Mock Ollama responses
#   - mock_chroma_client: In-memory ChromaDB instance
#   - session_cache: Ephemeral session cache
#
# Test naming: test_<function_name>.py or test_<class_name>.py
