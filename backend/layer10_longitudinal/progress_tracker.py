# Layer 10, Sub-Component: Progress Tracker
#
# Responsibility: Track progress on life dimensions across months and years.
#
# Life dimensions (from config/layer10.yaml):
#   - Career / Work
#   - Relationships / Social
#   - Health / Fitness
#   - Mental Health / Wellbeing
#   - Learning / Growth
#   - Creative / Expression
#   - Financial / Stability
#   - Leisure / Balance
#
# For each dimension:
#   - Compute rolling progress score (0–100%)
#   - Track trend (improving, stable, declining)
#   - Identify initiatives/goals in that dimension
#   - Flag stagnation if no progress in > 30 days
#
# Main functions:
#   - compute_dimension_progress(dimension_id, lookback_weeks) -> ProgressDimension
#   - compute_all_dimensions(user_id) -> list[ProgressDimension]
#   - detect_stagnation(dimension_id) -> bool
#   - project_trend(dimension_id) -> TrendProjection
#
# Integration:
#   - Runs weekly (after weekly_summary)
#   - Reads from Layer 2 (memories), Layer 7 (goals)
#   - Output consumed by Layer 6 (proactivity)
#   - Output consumed by Layer 4 (long-term context)
#
# Design: Progress is computed from user's actual stated progress, not inferred.
