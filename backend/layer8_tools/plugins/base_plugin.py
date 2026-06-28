"""ToolPlugin — abstract base interface for all Layer 8 plugins (architecture doc §9).

Every integration (calendar, email, notes, reminders, web search) subclasses this and
implements ``capabilities()`` + ``execute()``. The base supplies default ``validate_parameters``
(driven by each capability's ``required_params``), and safe no-op defaults for ``undo``,
``is_healthy`` and ``authenticate`` so a plugin only overrides what it actually supports.

This uniform contract is what lets the Tool Manager treat plugins as swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.layer8_tools.schemas import (
    Capability,
    ToolResult,
    ValidationResult,
)


class ToolPlugin(ABC):
    """Uniform interface the Tool Manager calls every integration through."""

    name: str = "plugin"

    @abstractmethod
    def capabilities(self) -> list[Capability]:
        """Operations this plugin exposes, with risk/param metadata."""

    @abstractmethod
    def execute(self, operation: str, parameters: dict) -> ToolResult:
        """Perform ``operation`` with ``parameters`` and return a ToolResult."""

    # ── Helpers shared by all plugins ─────────────────────────────────────────
    def capability_for(self, operation: str) -> Optional[Capability]:
        for cap in self.capabilities():
            if cap.operation == operation:
                return cap
        return None

    def supports(self, operation: str) -> bool:
        return self.capability_for(operation) is not None

    def validate_parameters(self, operation: str, parameters: dict) -> ValidationResult:
        cap = self.capability_for(operation)
        if cap is None:
            return ValidationResult(valid=False, errors=[f"unknown operation: {operation}"])
        parameters = parameters or {}
        missing = [
            p for p in cap.required_params
            if p not in parameters or parameters[p] in (None, "")
        ]
        if missing:
            return ValidationResult(
                valid=False, errors=[f"missing required parameter: {p}" for p in missing])
        return ValidationResult(valid=True)

    # ── Overridable defaults ──────────────────────────────────────────────────
    def undo(self, undo_token: str) -> bool:
        """Reverse a prior action. Base default: nothing is undoable."""
        return False

    def is_healthy(self) -> bool:
        return True

    def authenticate(self) -> bool:
        return True
