"""SC-1 bound confirmation-token bookkeeping (architecture doc §5.1).

Split out of ``tool_manager.py``: the ``_Pending`` record and the fingerprint hash that
binds a confirmation token to one exact ``(tool, operation, parameters, user_id)`` action.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class Pending:
    """A confirmation awaiting the user, bound to one exact action + user."""
    fingerprint: str
    tool_name: str
    operation: str
    parameters: dict
    action_type: str
    user_id: Optional[str]
    session_id: Optional[str]
    tier: str = "soft"          # carried so a pending-list view reports the real gate…
    reversible: bool = True     # …and whether the awaiting action can be undone (HARD/irreversible)


def fingerprint(tool_name: str, operation: str, parameters: dict, user_id) -> str:
    """Stable hash binding a confirmation token to a specific action and user (§5.1)."""
    payload = json.dumps(
        {"tool": tool_name, "operation": operation,
         "parameters": parameters or {}, "user_id": user_id},
        sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
