# Schemas for Layer 1 — Input Perception
#
# This module defines all data structures used by Layer 1's temporal resolver and implicit signal extractor.
#
# Key schemas:
#   - InputPerceptionPacket: The complete output of Layer 1, consumed by all downstream layers
#   - CircadianBand: Enum of time-of-day categories (late_night, early_morning, morning, afternoon, evening, night)
#   - SessionGapCategory: Enum for time since last user message (immediate, short, medium, long, extended, crisis_hiatus)
#   - TemporalContextObject: Rich timestamp metadata including timezone, circadian band, session gap, anomaly flags
#   - ImplicitSignalPacket: Extracted signals (typing_speed, pause_patterns, correction_patterns, emoji usage, etc.)
#   - MultimodalNormalization: Normalized representation of non-text input (voice prosody, image description, etc.)
#
# Design principle: All fields are immutable after creation. These are read-only contract objects.
