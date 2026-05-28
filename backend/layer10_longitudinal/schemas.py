# Schemas for Layer 10 — Longitudinal Life Layer
#
# Defines structures for life narrative, weekly summaries, progress tracking, and retrospectives.
#
# Key schemas:
#   - WeeklySummary: Digest of the week (emotional arc, topic themes, goal progress, key events)
#   - NarrativeChapter: A phase in user's life story (chapter_id, title, date_range, events, theme)
#   - LifeDimension: A dimension of life being tracked (e.g., "career," "relationships," "health")
#   - ProgressDimension: Progress on a specific life dimension (dimension_id, progress_score, trend)
#   - TurningPoint: A significant transition or inflection point in narrative
#   - RetrospectiveRecord: Generated retrospective (1-week, 1-month, 1-year, milestone)
#
# Design: All Layer 10 structures are read-only after creation (immutable historical record).
# They are synthesized from Layer 2 (memory) and Layer 7 (goals) but form their own hierarchy.
