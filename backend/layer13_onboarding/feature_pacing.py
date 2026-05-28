# Layer 13, Sub-Component: Feature Pacing
#
# Responsibility: Control which capabilities are unlocked during cold start.
#
# Feature unlock timeline:
#   - From start: Basic chat, memory formation (early)
#   - After 2-3 messages: Relationship tracking unlocked
#   - After 5 messages or 1 day: Goal tracking unlocked
#   - After graduation: Proactivity, advanced features unlocked
#   - Special: Safety/crisis detection is ALWAYS on
#
# Main functions:
#   - is_feature_ready(feature_name, user_id) -> bool
#   - get_feature_readiness_profile(user_id) -> FeatureReadinessProfile
#   - unlock_feature(feature_name, user_id) -> None
#
# Integration:
#   - Consulted by Layer 4 (prompt building) to suppress advanced context
#   - Consulted by Layer 6 (proactivity) to suppress proactive messages during cold start
#   - Consulted by pipeline to route to System 1 vs System 2
#   - Config read from config/layer13.yaml
#
# Design: Features are unlocked as system becomes ready, not arbitrarily held back.
