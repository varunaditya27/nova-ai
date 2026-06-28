"""Email plugin (architecture doc §9.2).

Draft-first by design: Nova composes a draft (SOFT), the user reviews, and only an explicit
HARD confirmation sends it. Sending is irreversible and reaches outside Nova, so ``undo`` on a
sent message returns False — the one operation in Layer 8 that genuinely cannot be taken back.
Reads are AUTO. A real provider is supplied via an injected adapter; default is in-memory.
"""

from __future__ import annotations

import uuid

from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.schemas import (
    ActionType,
    Capability,
    ConfirmationTier,
    RiskLevel,
    ToolOutcome,
    ToolResult,
)


class EmailPlugin(ToolPlugin):
    name = "email"

    def __init__(self) -> None:
        self._drafts: dict[str, dict] = {}
        self._sent: dict[str, dict] = {}
        self._undo_log: dict[str, str] = {}  # token -> draft_id (only drafts are undoable)

    def capabilities(self) -> list[Capability]:
        return [
            Capability("draft", ActionType.CREATE.value, "Draft an email",
                       default_tier=ConfirmationTier.SOFT.value, reversible=True,
                       external_impact=False, required_params=["to", "body"]),
            Capability("send", ActionType.SEND.value, "Send a drafted email",
                       default_tier=ConfirmationTier.HARD.value, reversible=False,
                       external_impact=True, risk_level=RiskLevel.HIGH.value,
                       required_params=["draft_id"]),
            Capability("read_inbox", ActionType.READ.value, "Read inbox messages",
                       default_tier=ConfirmationTier.AUTO.value),
            Capability("list_labels", ActionType.READ.value, "List inbox labels",
                       default_tier=ConfirmationTier.AUTO.value),
        ]

    def execute(self, operation: str, parameters: dict) -> ToolResult:
        parameters = parameters or {}
        if operation == "draft":
            return self._draft(parameters)
        if operation == "send":
            return self._send(parameters)
        if operation == "read_inbox":
            return ToolResult(self.name, "read_inbox", ToolOutcome.SUCCESS.value,
                              result_summary="inbox read", data=[])
        if operation == "list_labels":
            return ToolResult(self.name, "list_labels", ToolOutcome.SUCCESS.value,
                              data=["inbox", "sent", "drafts"])
        return ToolResult(self.name, operation, ToolOutcome.FAILURE.value,
                          error_message=f"unsupported operation: {operation}")

    def _draft(self, params: dict) -> ToolResult:
        draft_id = uuid.uuid4().hex
        self._drafts[draft_id] = {
            "draft_id": draft_id, "to": params["to"],
            "subject": params.get("subject", ""), "body": params["body"],
            "attachments": params.get("attachments", []),
        }
        token = uuid.uuid4().hex
        self._undo_log[token] = draft_id
        return ToolResult(self.name, "draft", ToolOutcome.SUCCESS.value,
                          result_summary=f"Drafted email to {params['to']}",
                          data={"draft_id": draft_id}, undo_token=token)

    def _send(self, params: dict) -> ToolResult:
        draft_id = params["draft_id"]
        draft = self._drafts.pop(draft_id, None)
        if draft is None:
            return ToolResult(self.name, "send", ToolOutcome.FAILURE.value,
                              error_message="draft not found")
        message_id = uuid.uuid4().hex
        self._sent[message_id] = draft
        # No undo token: a sent email cannot be recalled.
        return ToolResult(self.name, "send", ToolOutcome.SUCCESS.value,
                          result_summary=f"Sent email to {draft['to']}",
                          data={"message_id": message_id})

    def undo(self, undo_token: str) -> bool:
        draft_id = self._undo_log.pop(undo_token, None)
        if draft_id is None:
            return False
        return self._drafts.pop(draft_id, None) is not None
