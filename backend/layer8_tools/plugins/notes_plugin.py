# Notes Plugin
#
# Integrates with note-taking apps (Notion, Obsidian) or markdown files.
# Captures thoughts and context for later retrieval.
#
# Actions:
#   - create_note(title, content, tags) -> NoteID
#   - list_notes(query, tag_filter) -> list[Note]
#   - append_to_note(note_id, content) -> None
#   - delete_note(note_id) -> bool
#
# Implementation notes:
#   - Supports multiple backends (Notion API, local markdown files, Obsidian vault)
#   - AUTO confirmation for create/append
#   - SOFT confirmation for delete
#   - Full undo support (deleted notes archived, not permanently removed)
#   - Can be queried by Layer 2 (Memory) for retrieval
