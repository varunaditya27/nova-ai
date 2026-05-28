# Email Plugin
#
# Integrates with email providers (Gmail, Outlook, etc.).
# Draft-focused: can draft emails and ask for confirmation before sending.
#
# Actions:
#   - draft_email(to, subject, body) -> DraftID
#   - send_email(draft_id) -> MessageID  [HARD confirmation tier]
#   - read_inbox(query) -> list[Message]  [read-only]
#   - list_labels() -> list[Label]
#
# Implementation notes:
#   - Drafts are reversible; sending is not
#   - Send action has HARD confirmation tier (must be explicitly confirmed)
#   - Read operations are AUTO (no personal data leakage risk)
#   - Body generation via LLM (user-approved before sending)
#   - Undo support: Can draft-save but not un-send once sent
