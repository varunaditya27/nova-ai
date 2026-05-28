# SQLAlchemy Engine
#
# Responsibility: Create and manage the SQLite engine and session factory.
#
# Provides:
#   - create_engine(database_url) -> Engine
#   - SessionLocal: Session factory for dependency injection
#   - get_session() -> Generator[Session, None, None]  (context manager)
#
# Configuration:
#   - DATABASE_URL from environment or config (e.g., sqlite:///./nova-data/memory.db)
#   - Connection pooling (if using networked DB in future)
#   - Echo flag for SQL logging (dev only)
#
# Integration:
#   - Used by all models for ORM
#   - Used by FastAPI dependencies (api/dependencies.py)
