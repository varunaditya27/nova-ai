"""Enumerations for Layer 4 — Persona, Personality & Response Generation."""

from __future__ import annotations

from enum import Enum


# ── SC-2 Relationship enums ─────────────────────────────────────────────────
class RelationshipStage(str, Enum):
    """Qualitative relationship phase (architecture doc §4.2)."""

    NEW = "new"                      # 0–3 sessions; first contact
    ACQUAINTANCE = "acquaintance"    # 4–15 sessions; getting to know
    DEVELOPING = "developing"        # 16–40 sessions; real depth forming
    ESTABLISHED = "established"      # 41–100 sessions; trusted, consistent
    CLOSE = "close"                  # 100+ sessions; genuinely close


class MemoryReferencePolicy(str, Enum):
    """How explicitly Nova may bring up past memories (architecture doc §4.4)."""

    NONE = "none"
    SOFT = "soft"        # vague: "I remember you mentioned something like this"
    EPISODIC = "episodic"  # can reference specific episodes
    FULL = "full"        # full episodic + semantic pattern references


# ── SC-3 Voice / tone enums ─────────────────────────────────────────────────
class Register(str, Enum):
    FORMAL = "formal"
    PROFESSIONAL = "professional"
    NATURAL = "natural"
    CASUAL = "casual"
    INTIMATE = "intimate"


class SentenceLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    MIXED = "mixed"


class ParagraphDensity(str, Enum):
    SPARSE = "sparse"
    NORMAL = "normal"
    DENSE = "dense"


class VocabularyTier(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    ELEVATED = "elevated"
    TECHNICAL = "technical"


class ContractionPolicy(str, Enum):
    ALWAYS = "always"
    PREFERRED = "preferred"
    AVOID = "avoid"
    NEVER = "never"


class HumorMode(str, Enum):
    NONE = "none"
    SUBTLE = "subtle"
    MODERATE = "moderate"
    PLAYFUL = "playful"


class HumorType(str, Enum):
    DRY = "dry"
    WORDPLAY = "wordplay"
    ABSURDIST = "absurdist"
    WARM = "warm"


class TargetResponseLength(str, Enum):
    VERY_SHORT = "very_short"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    ADAPTIVE = "adaptive"


class QuestionType(str, Enum):
    OPEN = "open"
    SPECIFIC = "specific"
    CHECKING_IN = "checking_in"
    NONE = "none"


class SelfDisclosureDepth(str, Enum):
    NONE = "none"
    SURFACE = "surface"
    MODERATE = "moderate"


# ── SC-4 Drift enums ────────────────────────────────────────────────────────
class DriftType(str, Enum):
    SYCOPHANTIC_CAPITULATION = "sycophantic_capitulation"
    IDENTITY_CONTRADICTION = "identity_contradiction"
    FABRICATED_EMOTION = "fabricated_emotion"
    HARMFUL_VALIDATION = "harmful_validation"
    ROLE_ABANDONMENT = "role_abandonment"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedAction(str, Enum):
    PROCEED = "proceed"
    ADD_CAVEAT = "add_caveat"
    REDIRECT = "redirect"
    HOLD_POSITION = "hold_position"
    REFUSE_GRACEFULLY = "refuse_gracefully"
