# Layer 1 — Input Perception & Temporal Awareness
#
# This layer transforms raw incoming events into rich, structured InputPerceptionPacket objects.
# It is the first processor in the pipeline—running before any reasoning, memory, or response generation.
#
# Core responsibility: Extract temporal context, implicit signals, and multimodal semantics
# from a raw user message so that all downstream layers work with semantic-rich, contextualized input.
#
# Main components:
#   - temporal_resolver: Maps message timestamps to circadian bands, session gaps, anomalies
#   - thread_tracker: Manages pending narrative threads and follow-up surfacing
#   - schemas: InputPerceptionPacket, SessionGapCategory, CircadianBand enums
#
# Contract: Produces a read-only InputPerceptionPacket that every downstream layer consumes.
# No downstream layer re-derives temporal logic independently.
