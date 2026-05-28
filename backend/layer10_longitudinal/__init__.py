# Layer 10 — Longitudinal Life Layer
#
# Core question: What does it mean for Nova to have known someone across months and years?
#
# This layer looks backward across months and years, and forward across the user's entire known arc.
# It is the only layer that operates at the timescale of a life being lived.
#
# Central claim: A companion who holds your history is categorically different from one who responds
# well in the present moment. Growth is only visible with a before-state. Patterns only emerge
# from repetition across long durations.
#
# What makes Nova feel like a presence instead of a tool lives in this layer.
#
# Main components:
#   - life_narrative_engine.py: Continuous construction of user's life story as narrative arc
#   - weekly_summary.py: Weekly digest generation from sessions + goal data
#   - narrative_arc.py: Chapter boundary detection, turning point identification
#   - progress_tracker.py: Life dimension progress across months/years
#   - retrospective.py: Retrospective generation on milestone or request
#   - schemas.py: WeeklySummary, NarrativeChapter, LifeDimension, TurningPoint
#
# Execution model: Entirely asynchronous (not per-message). Background jobs on schedule.
# Output passed downstream to Layer 6 (proactivity) and Layer 4 (response generation).
