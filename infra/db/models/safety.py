# Safety Models (Layer 11)
#
# ORM models for:
#   - SafetyRecord: Log of all crisis signals and escalations
#   - DependencyScoreRecord: Longitudinal unhealthy reliance monitoring
#   - GuardrailViolationLog: Times Nova detected/suppressed manipulation risks
#
# Not encrypted (safety should be auditable even if compromise occurs).
