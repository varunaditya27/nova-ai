# Test: Crisis Classifier
#
# Tests:
#   - Detect crisis signals: text patterns, temporal anomalies, emotional intensity, prior vulnerabilities
#   - Classify crisis level (0-4: NONE to IMMINENT)
#   - Handle ambiguous cases (returns confidence scores)
#   - Validate crisis detection is conservative (minimize false positives)
#
# Fixtures: db_session, sample_conversations
