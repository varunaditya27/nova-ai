# SQLite Database Layer
#
# Everything related to SQLite persistence via SQLAlchemy.
#
# Main components:
#   - engine.py: create_engine() + SessionLocal factory
#   - base.py: declarative_base() (single source of truth for all models)
#   - models/: One file per domain (session, memory, persona, relationship, etc.)
#   - migrations/: Alembic migrations (auto-generated via declarative_base)
#
# Core principle: All models inherit from base. Alembic autodiscovers all models.
# No giant models.py. One model file per domain.
