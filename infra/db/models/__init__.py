"""ORM models mapping per-layer relational state. Importing this registers every table on Base.metadata."""
from __future__ import annotations

from infra.db.models.session import Session
from infra.db.models.message import ConversationMessage
from infra.db.models.memory import (
    EpisodicMemory, SemanticMemory, IdentityMemory, MemoryAudit, UserWorldModel, NarrativeChain,
)
from infra.db.models.persona import PersonaState
from infra.db.models.relationship import RelationshipState
from infra.db.models.social import SocialGraph, SocialEvent, SocialPattern
from infra.db.models.goals import Goal
from infra.db.models.proactivity import ProactiveItem
from infra.db.models.safety import SafetyEvent
from infra.db.models.privacy import PrivacyAudit
from infra.db.models.longitudinal import (
    LongitudinalSummary, BehavioralPattern, LifeCalendarEntry, Retrospective,
)
from infra.db.models.tools import ToolAction
from infra.db.models.output_prefs import OutputPref
from infra.db.models.onboarding import OnboardingState
from infra.db.models.sync import SyncDelta
from infra.db.models.format_profile import FormatProfile

__all__ = [
    "Session", "ConversationMessage",
    "EpisodicMemory", "SemanticMemory", "IdentityMemory", "MemoryAudit", "UserWorldModel",
    "NarrativeChain",
    "PersonaState", "RelationshipState", "Goal", "ProactiveItem", "SafetyEvent",
    "PrivacyAudit", "LongitudinalSummary", "ToolAction", "OutputPref", "OnboardingState",
    "SyncDelta", "SocialGraph", "SocialEvent", "SocialPattern", "FormatProfile",
    "BehavioralPattern", "LifeCalendarEntry", "Retrospective",
]
