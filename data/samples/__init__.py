# Sample Data for Development & Testing
#
# Purpose: Pre-populated memories, relationships, goals for testing
#
# Contents:
#   - sample_episodic_memories.json: Example episodic memories (diverse topics, emotions, timestamps)
#   - sample_relationships.json: Example relationships (various stages, tie strengths)
#   - sample_goals.json: Example goals (active, completed, abandoned)
#   - sample_personality_vector.json: Example personality profile
#   - sample_conversations.json: Multi-turn conversation examples
#
# Usage:
#   - Used by scripts/seed_db.py to populate dev database
#   - Used by tests/conftest.py fixtures
#   - Loaded by Python: import json; samples = json.load(open('samples/...'))
#
# Format:
#   - Valid JSON (no comments in actual files)
#   - Schema matches corresponding database models
#   - Timestamps in ISO 8601 format
#   - Encryption ready (but samples are unencrypted for readability)
