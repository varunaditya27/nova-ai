# Data Directory
#
# Persistent data storage for Nova AI
#
# Subdirectories:
#   - chroma/: ChromaDB persistent storage (vector embeddings)
#   - nova.db: SQLite database (all records)
#   - samples/: Example data for testing & seeding
#   - migrations/: (Actually in infra/db/migrations/, but reference here)
#   - exports/: User data exports (memory audits, JSON, CSV)
#
# Initialization:
#   On first run:
#     1. Create nova.db (SQLAlchemy auto-creates tables)
#     2. Create chroma/ directory (ChromaDB auto-initializes)
#     3. Seed with sample data (optional: python -m scripts.seed_db)
#
# Backup:
#   - Regular backups of nova.db (SQLite native backup)
#   - Encrypted backup of chroma/ (vector store)
#   - User export audit trail stored here
#
# Privacy:
#   - All data at rest encrypted (Layer 12 encryption_manager)
#   - No PII in logs (Layer 9 middleware logging.py)
