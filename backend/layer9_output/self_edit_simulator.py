# Layer 9, Sub-Component: Self-Edit Simulator
#
# Responsibility: Simulate human-like self-editing: start typing, delete phrase, resume.
#
# Sequence: "I think you should... actually, that's not right... what I mean is, you might..."
# Shows as: "I think you should" → [DELETE] → "what I mean is, you might..."
#
# Main functions:
#   - detect_self_edit_points(response_text, mode) -> list[SelfEditPoint]
#   - generate_self_edit_sequence(text, edit_points) -> list[EditEvent]
#   - should_self_edit(context) -> bool
#
# Integration:
#   - Called by interaction_orchestrator
#   - Detects natural re-phrasing points in response text
#   - Emits ShowPhraseEvent → DeleteEvent → ResumeEvent to frontend
#   - Controlled by crisis_mode (disabled if crisis_mode_active)
#
# Design: Self-editing humanizes the response but should be infrequent.
# User learns this is a design feature, not a mistake. Only on non-crisis responses.
