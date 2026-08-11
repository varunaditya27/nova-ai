"""SC-3 Feature Introduction Pacing schemas (architecture doc §6.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IntroductionStyle(str, Enum):
    SILENT = "silent"
    SOFT_OFFER = "soft_offer"
    EXPLAINED = "explained"


@dataclass
class FeatureTechnicalPrereqs:
    minimum_sessions: int = 0
    minimum_exchanges: int = 0
    required_context_fields: list = field(default_factory=list)
    cold_start_must_be_complete: bool = False


@dataclass
class FeatureRelationalPrereqs:
    user_has_shared_personally: bool = False
    positive_engagement_sessions: int = 0
    no_negative_surprise_events: bool = False
    user_has_returned_voluntarily: int = 0


@dataclass
class FeatureReadinessProfile:
    feature_id: str
    layer: int
    feature_name: str
    technical_prereqs: FeatureTechnicalPrereqs
    relational_prereqs: FeatureRelationalPrereqs
    introduction_style: str
    trigger_condition: str
    intro_message: Optional[str] = None


@dataclass
class FeatureIntroductionEvent:
    feature_id: str
    introduction_style: str
    intro_message: Optional[str]
    triggered_at_session: int
