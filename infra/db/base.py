# SQLAlchemy Base
#
# Responsibility: Declare the declarative_base() that all models inherit from.
#
# Provides:
#   - Base class for all models
#   - Metadata registry (used by Alembic for auto-discovery)
#
# Principle: Single base. All models inherit from it.
# This ensures Alembic sees all models automatically.
#
# No model definitions here. Just the base class.
