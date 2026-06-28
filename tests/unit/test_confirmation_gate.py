"""Tests for SC: Confirmation Gate (architecture doc §4 — risk → confirmation tier)."""

from backend.layer8_tools import confirmation_gate as cg
from backend.layer8_tools.schemas import (
    ActionType,
    ConfirmationRequest,
    ConfirmationTier,
    RiskLevel,
)


# ── Base action → tier mapping (§4.2) ────────────────────────────────────────
def test_read_is_auto():
    assert cg.compute_confirmation_tier(ActionType.READ.value) == ConfirmationTier.AUTO.value


def test_search_is_auto():
    assert cg.compute_confirmation_tier(ActionType.SEARCH.value) == ConfirmationTier.AUTO.value


def test_create_is_soft():
    assert cg.compute_confirmation_tier(ActionType.CREATE.value) == ConfirmationTier.SOFT.value


def test_update_is_soft():
    assert cg.compute_confirmation_tier(ActionType.UPDATE.value) == ConfirmationTier.SOFT.value


def test_delete_is_hard():
    assert cg.compute_confirmation_tier(ActionType.DELETE.value) == ConfirmationTier.HARD.value


def test_send_is_hard():
    assert cg.compute_confirmation_tier(ActionType.SEND.value) == ConfirmationTier.HARD.value


# ── Escalation rules (§4.3) ──────────────────────────────────────────────────
def test_high_risk_forces_hard():
    tier = cg.compute_confirmation_tier(ActionType.READ.value, risk_level=RiskLevel.HIGH.value)
    assert tier == ConfirmationTier.HARD.value


def test_irreversible_external_is_hard():
    tier = cg.compute_confirmation_tier(
        ActionType.CREATE.value, reversible=False, external_impact=True)
    assert tier == ConfirmationTier.HARD.value


def test_irreversible_non_external_escalates_to_soft():
    # A read that cannot be undone is still at least SOFT (never silently AUTO).
    tier = cg.compute_confirmation_tier(ActionType.READ.value, reversible=False)
    assert tier == ConfirmationTier.SOFT.value


def test_tier_only_ratchets_up_never_down():
    # base_tier override cannot lower a delete below its computed HARD floor.
    tier = cg.compute_confirmation_tier(
        ActionType.DELETE.value, base_tier=ConfirmationTier.AUTO.value)
    assert tier == ConfirmationTier.HARD.value


def test_capability_base_tier_can_raise():
    # A plugin may declare a CREATE op as HARD even though CREATE defaults to SOFT.
    tier = cg.compute_confirmation_tier(
        ActionType.CREATE.value, base_tier=ConfirmationTier.HARD.value)
    assert tier == ConfirmationTier.HARD.value


# ── ConfirmationRequest assembly (§4.4) ──────────────────────────────────────
def test_get_confirmation_request_carries_tier_and_description():
    req = cg.get_confirmation_request(
        tool_name="email", action_type=ActionType.SEND.value,
        action_description="Send email to alex@example.com", tier=ConfirmationTier.HARD.value,
        risk_level=RiskLevel.HIGH.value, reversible=False, parameters={"to": "alex@example.com"})
    assert isinstance(req, ConfirmationRequest)
    assert req.tier == ConfirmationTier.HARD.value
    assert req.tool_name == "email"
    assert "alex@example.com" in req.action_description
    assert req.request_id  # non-empty


def test_auto_requests_need_no_user_prompt():
    assert cg.requires_user_confirmation(ConfirmationTier.AUTO.value) is False
    assert cg.requires_user_confirmation(ConfirmationTier.SOFT.value) is True
    assert cg.requires_user_confirmation(ConfirmationTier.HARD.value) is True
