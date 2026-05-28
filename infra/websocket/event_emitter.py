# Event Emitter
#
# Responsibility: Typed event emission to WebSocket clients.
#
# Main functions:
#   - emit_thinking(websocket, duration_ms) -> None
#   - emit_typing(websocket, tokens) -> None
#   - emit_backchannel(websocket, type, intensity) -> None
#   - emit_completed(websocket) -> None
#   - emit_audio(websocket, audio_bytes) -> None
#
# Events are JSON-serialized and sent over WebSocket.
# Frontend subscribes to event stream and renders accordingly.
