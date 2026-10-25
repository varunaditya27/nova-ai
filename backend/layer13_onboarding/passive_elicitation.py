"""Layer 13 SC-1 — Passive Elicitation Engine (architecture doc §4.5).

Runs on every incoming message from the first message onward, extracting context signals
*without asking the user anything*. Pure regex + heuristics, no LLM calls (perf target <20ms).
Each extractor is exception-safe at the orchestrator level: a single failing extractor is
logged and skipped, never corrupting the rest of the PassiveSignalBundle (§9 degraded mode).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from .schemas import (
    CommunicationStyleUpdate,
    DisclosureComfort,
    EmotionalExpressionStyle,
    LifeContextSignals,
    NamedPersonSignal,
    PassiveSignalBundle,
    TopicApproach,
    UrgencySignal,
    VocabularyRegister,
)

logger = logging.getLogger(__name__)

_FORMAL_MARKERS = ["therefore", "however", "furthermore", "regarding", "consequently"]
_INFORMAL_MARKERS = ["lol", "tbh", "ngl", "kinda", "gonna", "wanna", "idk"]
_EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]|[☀-⟿]")

_DIRECT_EMOTION_WORDS = [
    "anxious", "scared", "angry", "sad", "happy", "excited",
    "frustrated", "overwhelmed", "confused", "proud", "hurt",
]
_INDIRECT_HEDGES = [
    "just", "kind of", "sort of", "a bit", "weird", "off",
    "not great", "not bad", "fine i guess",
]
_HEDGING_PHRASES = [
    "i might be wrong", "not sure but", "just my opinion", "i think", "maybe", "could be wrong",
]
_OPINION_REQUESTS = ["what do you think", "your opinion", "what would you do"]
_FACT_REQUESTS = ["how do i", "what is", "can you explain", "what's the best way"]

_PERSONAL_DISCLOSURE_MARKERS = [
    r"I (am|was|feel|felt|have|had|went|did|said|told|made)",
    r"my (friend|family|mom|dad|sister|brother|partner|job|life|problem)",
    r"(I'm|im) (going through|dealing with|struggling with)",
]
_RELATIONSHIP_CONTEXT_PATTERN = re.compile(
    r"(my\s+)?(friend|sister|brother|mom|dad|partner|boyfriend|girlfriend|"
    r"roommate|colleague|professor|boss)\s+([A-Z][a-z]+)",
    re.IGNORECASE,
)
_STUDENT_SIGNALS = ["exam", "class", "semester", "assignment", "campus",
                    "professor", "study", "college", "university", "degree", "student",
                    "undergrad", "btech", "b.tech", "hostel", "lecture", "engineering"]
_WORK_SIGNALS = ["work", "job", "office", "meeting", "deadline", "manager",
                 "client", "salary", "career", "company"]
_HIGH_URGENCY_PATTERNS = ["asap", "urgent", "need to know now", "happening right now",
                          "tonight", "tomorrow morning", "in an hour"]
_EXPLORATORY_PATTERNS = ["just wondering", "curious", "was thinking", "what do you think",
                         "no rush", "whenever"]


class PassiveElicitationEngine:
    """Eight extractors over the user's raw text + session history."""

    def extract(self, message: str, message_index: int, session_number: int,
                timestamp: datetime, session_history: list) -> PassiveSignalBundle:
        bundle = PassiveSignalBundle()
        runs = {
            "vocabulary_register": lambda: self._extract_vocabulary_register(message),
            "emotional_expression_style": lambda: self._extract_emotional_style(message, session_history),
            "topic_approach": lambda: self._extract_topic_approach(message, session_history),
            "self_disclosure_comfort": lambda: self._extract_disclosure_comfort(message, session_history),
            "temporal_pattern": lambda: self._extract_temporal_pattern(timestamp, session_number),
            "named_entities": lambda: self._extract_named_people(message),
            "life_context_signals": lambda: self._extract_life_context(message),
            "urgency_signals": lambda: self._extract_urgency(message),
            "communication_style": lambda: self._extract_communication_style(message, session_history),
        }
        for attr, fn in runs.items():
            try:
                setattr(bundle, attr, fn())
            except Exception:  # one failing extractor must not corrupt the bundle (§9)
                logger.exception("passive extractor %s failed; skipping", attr)
        return bundle

    # ── Extractor 1: vocabulary register ─────────────────────────────────────
    def _extract_vocabulary_register(self, message: str) -> VocabularyRegister:
        words = message.split()
        avg_word_length = sum(len(w) for w in words) / max(len(words), 1)
        sentence_count = len([s for s in re.split(r"[.!?]+", message) if s.strip()])
        avg_sentence_length = len(words) / max(sentence_count, 1)
        low = message.lower()
        formality_score = (sum(1 for m in _FORMAL_MARKERS if m in low) -
                           sum(1 for m in _INFORMAL_MARKERS if m in low))
        return VocabularyRegister(
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            uses_emoji=bool(_EMOJI_RE.search(message)),
            formality_delta=formality_score,
            message_length=len(words),
        )

    # ── Extractor 2: emotional expression style ──────────────────────────────
    def _extract_emotional_style(self, message: str, history: list) -> EmotionalExpressionStyle:
        low = message.lower()
        direct_count = sum(1 for w in _DIRECT_EMOTION_WORDS if w in low)
        indirect_count = sum(1 for h in _INDIRECT_HEDGES if h in low)
        confidence = min(len(history) / 10, 1.0) if len(history) >= 3 else 0.2
        return EmotionalExpressionStyle(
            style=("direct" if direct_count > indirect_count else "indirect"),
            confidence=confidence,
        )

    # ── Extractor 3: topic approach ──────────────────────────────────────────
    def _extract_topic_approach(self, message: str, history: list) -> TopicApproach:
        low = message.lower()
        context_building = len(message.split()) > 50 and message.strip().endswith("?")
        return TopicApproach(
            hedges_views=any(h in low for h in _HEDGING_PHRASES),
            seeks_opinions=any(o in low for o in _OPINION_REQUESTS),
            seeks_facts=any(f in low for f in _FACT_REQUESTS),
            context_builder=context_building,
        )

    # ── Extractor 4: self-disclosure comfort ─────────────────────────────────
    def _extract_disclosure_comfort(self, message: str, history: list) -> DisclosureComfort:
        signals = sum(1 for p in _PERSONAL_DISCLOSURE_MARKERS
                      if re.search(p, message, re.IGNORECASE))
        density = signals / max(len(message.split()) / 20, 1)
        density = min(density, 1.0)
        return DisclosureComfort(
            density=density,
            level=("high" if density > 0.3 else "medium" if density > 0.1 else "low"),
        )

    # ── Extractor 5: named people ────────────────────────────────────────────
    def _extract_named_people(self, message: str) -> list:
        people = []
        for match in _RELATIONSHIP_CONTEXT_PATTERN.finditer(message):
            people.append(NamedPersonSignal(
                name=match.group(3),
                relationship_type=match.group(2).lower(),
                confidence=0.85,
            ))
        return people

    # ── Extractor 6: life context ────────────────────────────────────────────
    def _extract_life_context(self, message: str) -> LifeContextSignals:
        low = message.lower()
        student_score = sum(1 for s in _STUDENT_SIGNALS if s in low)
        work_score = sum(1 for s in _WORK_SIGNALS if s in low)
        if student_score > 0 and student_score >= work_score:
            return LifeContextSignals("student", min(student_score * 0.3, 0.9))
        if work_score > 0:
            return LifeContextSignals("working", min(work_score * 0.3, 0.9))
        return LifeContextSignals(None, 0.0)

    # ── Extractor 7: urgency ─────────────────────────────────────────────────
    def _extract_urgency(self, message: str) -> UrgencySignal:
        low = message.lower()
        urgent = any(p in low for p in _HIGH_URGENCY_PATTERNS)
        exploratory = any(p in low for p in _EXPLORATORY_PATTERNS)
        return UrgencySignal(level=("high" if urgent else "low" if exploratory else "medium"))

    # ── Extractor 8: communication style ─────────────────────────────────────
    def _extract_communication_style(self, message: str, history: list) -> CommunicationStyleUpdate:
        lengths = [len(t.user_message.split()) for t in history] + [len(message.split())]
        avg_length = sum(lengths) / len(lengths)
        return CommunicationStyleUpdate(
            avg_user_message_length=avg_length,
            verbosity_preference=("concise" if avg_length < 20
                                  else "medium" if avg_length < 60 else "verbose"),
            sample_count=len(lengths),
        )

    # ── (temporal pattern: coarse circadian band; no PII) ────────────────────
    def _extract_temporal_pattern(self, timestamp: datetime, session_number: int) -> Optional[str]:
        if timestamp is None:
            return None
        h = timestamp.hour
        if h < 5 or h >= 23:
            return "late_night"
        if h < 12:
            return "morning"
        if h < 18:
            return "afternoon"
        return "evening"
