# Layer 13, Sub-Component: Active Elicitation Queue
#
# Responsibility: Prioritized queue of naturally-triggered questions.
#
# Questions are triggered, not forced. Examples:
#   - User mentions a person → queue "How long have you known them?"
#   - User mentions a goal → queue "Is this something you're actively working on?"
#   - User expresses emotion → queue "Is this typical for you, or is something unusual happening?"
#
# Queue management:
#   - Items prioritized by relevance (high = ask soon, low = optional, nice-to-know)
#   - Asked at most once per session per item
#   - Questions phrased to feel natural, not formulaic
#   - User can deflect; no pressure to answer
#
# Main functions:
#   - queue_elicitation_item(item: ElicitationItem) -> None
#   - get_next_item_for_session() -> ElicitationItem | None
#   - should_ask_in_this_session(item) -> bool
#   - receive_answer(item_id, answer) -> None
#
# Integration:
#   - Feeds elicitation questions into Layer 4 (prompt building)
#   - Called by cold_start_engine
#   - Reads from Layer 2 (what's been learned), Layer 3 (emotional context)
#
# Design: One question per session max. Questions feel natural, not procedural.
