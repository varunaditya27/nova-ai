# Schemas for Layer 9 — Output Delivery & Interaction Orchestration
#
# Defines all structures for orchestrated output, typing events, micro-interactions, and voice.
#
# Key schemas:
#   - OrchestratedOutput: Full event sequence to render (type-ordered, time-stamped)
#   - TypingEvent: Token-by-token streaming directive
#   - MicroInteractionPlan: Sequence of backchannels, pauses, self-edits
#   - FormatSpec: (register, markdown_policy, emoji_level, length_target)
#   - UserFormatProfile: Learned per-user format preferences
#   - SSMLDocument: Voice markup for prosody, rate, emphasis
#   - PauseDecision: When/how long to pause given context
#
# Design: All output events are ordered and timestamped. Rendering engine
# (in frontend) consumes this stream and produces the user-visible output.
