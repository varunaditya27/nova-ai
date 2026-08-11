"""SC-1 PersonaState types (architecture doc §3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DynamicPersonaProperty:
    """A lower-centrality identity property that evolves over interactions (§3.3)."""

    key: str
    value: str = ""
    centrality: float = 0.0          # 0.0–0.84 (below the core threshold)
    confidence: float = 0.0
    last_updated: Optional[datetime] = None
    evidence_count: int = 0
    is_user_specific: bool = True


@dataclass
class PersonaState:
    """The current, authoritative in-session persona (architecture doc §3.4)."""

    # Core identity (always present)
    name: str = "Nova"
    character_description: str = ""
    primary_orientation: str = ""
    honesty_commitment: str = ""

    # Expression parameters (assembled from dynamic properties)
    warmth_level: float = 0.7
    humor_allowed: bool = False
    humor_frequency: float = 0.25
    directness_level: float = 0.6
    technical_depth_allowed: bool = False
    intellectual_engagement_level: float = 0.5

    # Boundary policies (hard constraints — always True)
    will_not_fabricate_emotions: bool = True
    will_not_be_sycophantic: bool = True
    will_disagree_when_warranted: bool = True
    will_not_catastrophize: bool = True

    # Session-specific overrides
    session_tone_override: Optional[str] = None
    user_nickname_for_nova: Optional[str] = None
    known_sensitivities: list[str] = field(default_factory=list)

    # Provenance
    core_anchors_loaded: int = 0
    dynamic_properties_loaded: int = 0
    last_identity_update: Optional[datetime] = None
