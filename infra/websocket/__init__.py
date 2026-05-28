# WebSocket Infrastructure
#
# Real-time delivery of events to frontend (NextJS dashboard).
#
# Components:
#   - connection_manager.py: WebSocket session registry and lifecycle
#   - event_emitter.py: Typed event emitters (ThinkingEvent, TypingEvent, etc.)
#
# Event types:
#   - ThinkingEvent: "Nova is thinking..."
#   - TypingEvent: Token-by-token typing
#   - BackchannelEvent: "mm-hmm", "I see", etc.
#   - AudioEvent: Voice/audio output
#   - CompletedEvent: Response finished
