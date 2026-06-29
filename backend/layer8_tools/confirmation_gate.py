"""SC: Confirmation Gate (architecture doc §4).

Maps an operation's risk profile (action verb, reversibility, external impact, declared risk)
to a confirmation tier (AUTO / SOFT / HARD). The policy is deterministic and *conservative*:
the tier only ever ratchets up. A plugin may raise the floor via ``base_tier`` (e.g. mark a
create as HARD) but can never lower the computed floor below what the action verb demands.
"""

from __future__ import annotations

from backend.layer8_tools.schemas import (
    ActionType,
    ConfirmationRequest,
    ConfirmationTier,
    RiskLevel,
)

# Base tier per action verb (§4.2).
ACTION_TIER_BASE = {
    ActionType.READ.value:   ConfirmationTier.AUTO.value,
    ActionType.SEARCH.value: ConfirmationTier.AUTO.value,
    ActionType.CREATE.value: ConfirmationTier.SOFT.value,
    ActionType.UPDATE.value: ConfirmationTier.SOFT.value,
    ActionType.DELETE.value: ConfirmationTier.HARD.value,
    ActionType.SEND.value:   ConfirmationTier.HARD.value,
}

_TIER_ORDER = {
    ConfirmationTier.AUTO.value: 0,
    ConfirmationTier.SOFT.value: 1,
    ConfirmationTier.HARD.value: 2,
}
_ORDER_TIER = {v: k for k, v in _TIER_ORDER.items()}


def _max_tier(*tiers: str) -> str:
    """Return the highest (most cautious) of the given tiers."""
    return _ORDER_TIER[max(_TIER_ORDER.get(t, 1) for t in tiers if t is not None)]


def compute_confirmation_tier(
    action_type: str,
    reversible: bool = True,
    external_impact: bool = False,
    risk_level: str = RiskLevel.LOW.value,
    base_tier: str | None = None,
) -> str:
    """Resolve the confirmation tier for an operation (§4.3).

    A plugin's declared ``base_tier`` is authoritative as the *baseline* (it knows its own
    operation's stakes — e.g. a reversible reminder delete is AUTO); when none is given, the
    action-verb base applies. On top of that baseline sit **intrinsic escalation floors** that a
    plugin can never lower: high risk, irreversibility, and especially irreversible actions that
    reach outside Nova. These floors derive from the action's nature, not the plugin's opinion,
    so the gate can relax a verb's default downward but never drop below a safety floor.
    """
    tier = base_tier if base_tier is not None else ACTION_TIER_BASE.get(
        action_type, ConfirmationTier.SOFT.value)

    # Intrinsic escalation floors — each can only raise the tier.
    if risk_level == RiskLevel.HIGH.value:
        tier = _max_tier(tier, ConfirmationTier.HARD.value)
    if not reversible:
        # Irreversible + reaches outside Nova → HARD; irreversible alone → at least SOFT.
        tier = _max_tier(tier, ConfirmationTier.HARD.value if external_impact
                         else ConfirmationTier.SOFT.value)
    return tier


def requires_user_confirmation(tier: str) -> bool:
    """AUTO executes silently; SOFT/HARD need the user in the loop (§4.1)."""
    return tier != ConfirmationTier.AUTO.value


def get_confirmation_request(
    tool_name: str,
    action_type: str,
    action_description: str,
    tier: str,
    risk_level: str = RiskLevel.LOW.value,
    reversible: bool = True,
    parameters: dict | None = None,
) -> ConfirmationRequest:
    """Assemble a ConfirmationRequest to surface to the user (§4.4)."""
    return ConfirmationRequest(
        tool_name=tool_name,
        action_type=action_type,
        action_description=action_description,
        tier=tier,
        risk_level=risk_level,
        reversible=reversible,
        parameters=parameters or {},
    )
