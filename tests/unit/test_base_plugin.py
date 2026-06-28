"""Tests for the ToolPlugin base interface (architecture doc §9 — plugin contract)."""

import pytest

from backend.layer8_tools.plugins.base_plugin import ToolPlugin
from backend.layer8_tools.schemas import (
    ActionType,
    Capability,
    ToolOutcome,
    ToolResult,
    ValidationResult,
)


class _EchoPlugin(ToolPlugin):
    """Minimal concrete plugin used to exercise the base contract."""
    name = "echo"

    def capabilities(self):
        return [Capability(operation="say", action_type=ActionType.CREATE.value,
                           required_params=["text"])]

    def execute(self, operation, parameters):
        return ToolResult(tool_name=self.name, operation=operation,
                          outcome=ToolOutcome.SUCCESS.value, data=parameters.get("text"))


def test_abstract_base_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ToolPlugin()


def test_capabilities_returns_list_of_capability():
    caps = _EchoPlugin().capabilities()
    assert caps and all(isinstance(c, Capability) for c in caps)


def test_supports_known_operation():
    p = _EchoPlugin()
    assert p.supports("say") is True
    assert p.supports("nope") is False


def test_validate_parameters_flags_missing_required():
    res = _EchoPlugin().validate_parameters("say", {})
    assert isinstance(res, ValidationResult)
    assert res.valid is False and any("text" in e for e in res.errors)


def test_validate_parameters_passes_when_required_present():
    assert _EchoPlugin().validate_parameters("say", {"text": "hi"}).valid is True


def test_validate_unknown_operation_is_invalid():
    assert _EchoPlugin().validate_parameters("unknown", {}).valid is False


def test_execute_returns_tool_result():
    res = _EchoPlugin().execute("say", {"text": "hello"})
    assert res.outcome == ToolOutcome.SUCCESS.value and res.data == "hello"


def test_defaults_undo_health_auth():
    p = _EchoPlugin()
    assert p.undo("any-token") is False     # base default: nothing to undo
    assert p.is_healthy() is True
    assert p.authenticate() is True
