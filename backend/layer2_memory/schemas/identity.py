"""SC-4 Identity Memory types (docs/layer-2-architecture.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .enums import IdentityCategory


@dataclass
class BeliefUpdateEvent:
    updated_at: datetime
    prior_statement: str
    new_statement: str
    triggering_session_id: Optional[UUID] = None
    evidence_strength: float = 0.0
    update_reason: str = ""


@dataclass
class IdentityEvidence:
    """One session's contradictory evidence against a belief, with its own strength — distinct
    from ``BeliefUpdateEvent`` (that records an actual rewrite; this records evidence that hasn't
    (yet) crossed the update threshold). Structured so accumulated strength can genuinely be
    summed across sessions (§6.4) — a plain ``list[str]`` of summaries has nowhere to keep the
    per-event score."""
    summary: str
    strength: float = 0.0
    session_id: Optional[UUID] = None
    recorded_at: Optional[datetime] = None


@dataclass
class IdentityMemory:
    belief_id: UUID = field(default_factory=uuid4)
    category: IdentityCategory = IdentityCategory.OPINION
    statement: str = ""
    centrality: float = 0.5
    update_threshold: float = 0.625
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[IdentityEvidence] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    update_history: list[BeliefUpdateEvent] = field(default_factory=list)
    is_immutable: bool = False


@dataclass
class IdentityContradiction:
    belief_id: UUID
    evidence_summary: str
    contradiction_score: float
    session_id: Optional[UUID] = None
    strength: float = 0.0
