# Session Cache
#
# Responsibility: In-process working memory buffer for current turn.
# Holds working memory objects, session state, and transient data
# that does not need to persist to disk.
#
# Data stored:
#   - Current user_id, session_id, turn_number
#   - InputPerceptionPacket (Layer 1)
#   - Recalled memories (Layer 2)
#   - Emotion/intent vectors (Layer 3)
#   - Persona state (Layer 4)
#   - Goal context (Layer 7)
#   - Crisis flags (Layer 11)
#   - Cold start constraints (Layer 13)
#
# Main functions:
#   - initialize_session_cache(session_id) -> SessionCache
#   - store_layer_output(layer_name, output) -> None
#   - get_layer_input(layer_name) -> InputObject
#   - clear_session_cache() -> None
#
# Design: Ephemeral. Only for current turn. Not persisted.
#
# This is not the same as Layer 2 WorkingMemory. This is the turn-level buffer.
