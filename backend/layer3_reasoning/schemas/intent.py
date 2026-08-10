"""SC-3 Intent Classifier types (architecture doc §5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .emotion import ClassificationMethod


class IntentLabel(str, Enum):
    """What the user is trying to accomplish (architecture doc §5.2)."""

    # Relational / emotional.
    VENTING = "venting"
    SEEKING_VALIDATION = "seeking_validation"
    SEEKING_COMFORT = "seeking_comfort"
    SHARING_GOOD_NEWS = "sharing_good_news"
    CASUAL_CHAT = "casual_chat"
    CHECK_IN = "check_in"
    # Cognitive / task.
    SEEKING_ADVICE = "seeking_advice"
    SEEKING_INFORMATION = "seeking_information"
    THINKING_ALOUD = "thinking_aloud"
    PROBLEM_SOLVING = "problem_solving"
    GOAL_SETTING = "goal_setting"
    DECISION_SUPPORT = "decision_support"
    # Meta / relational.
    PROVIDING_UPDATE = "providing_update"
    EXPRESSING_GRATITUDE = "expressing_gratitude"
    EXPRESSING_COMPLAINT = "expressing_complaint"
    TESTING_NOVA = "testing_nova"
    REQUESTING_REFLECTION = "requesting_reflection"


class TopicDomain(str, Enum):
    """Subject matter of the conversation (architecture doc §5.5)."""

    ACADEMICS = "academics"
    CAREER = "career"
    RELATIONSHIPS = "relationships"
    HEALTH = "health"
    EXISTENTIAL = "existential"
    SOCIAL = "social"
    OTHER = "other"


@dataclass
class IntentClassification:
    """What the user needs from Nova right now (architecture doc §5)."""

    primary_intent: str = IntentLabel.CASUAL_CHAT.value
    secondary_intent: Optional[str] = None
    intent_confidence: float = 0.0
    needs_advice: bool = False
    needs_validation: bool = False
    prefers_no_advice: bool = False
    topic_domain: str = TopicDomain.OTHER.value
    classification_method: str = ClassificationMethod.HEURISTIC_ONLY.value
