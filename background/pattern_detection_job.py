# Pattern Detection Job
#
# Responsibility: Run weekly sweep for temporal-emotional pattern detection.
#
# Trigger: Weekly (configurable day, typically Sunday 2 AM)
#
# Executes:
#   - layer6_proactivity.pattern_detector.detect_patterns() for all users
#   - Detected patterns feed into proactive queue
#
# Performance: Typically 30 sec - 2 min depending on history volume
