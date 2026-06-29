"""SC-3 — Voice & SSML Synthesizer (architecture doc §5).

Turns a text response into a prosodically annotated SSML document and dispatches it to a TTS
backend. Voice is a first-class medium, not TTS-over-text: this adds prosody (§5.3), explicit
breaks (§5.4), a per-mode filler policy (§5.5), and voice content transforms that turn markdown
into spoken forms (§5.6). All randomness is injected (``rng``); any backend failure degrades to
a non-ok AudioResult so the caller can fall back to text (§9).
"""

from __future__ import annotations

import random as _random
import re
from typing import Optional

from backend.layer9_output.schemas import AudioResult, ProsodyParams, SSMLDocument

# Prosody table (architecture doc §5.3): mode → (rate, pitch).
PROSODY_TABLE = {
    "casual_chat":       ("medium", "+1"),
    "emotional_support": ("slow", "-1.5"),
    "crisis_support":    ("x-slow", "-2"),
    "celebration":       ("medium-fast", "+2.5"),
    "deep_reasoning":    ("slow", "+0"),
    "technical":         ("medium", "+0"),
    "task_help":         ("medium", "+0.5"),
}

SENTENCE_BREAK_MS = {
    "casual_chat": 200, "emotional_support": 450, "crisis_support": 650,
    "celebration": 120, "deep_reasoning": 300, "technical": 180, "task_help": 200,
}
CLAUSE_BREAK_MS = {
    "casual_chat": 80, "emotional_support": 200, "crisis_support": 300,
    "celebration": 60, "deep_reasoning": 150, "technical": 100, "task_help": 100,
}

FILLER_SOUNDS = ["um", "uh", "hmm", "well,", "you know,"]
FILLER_RATE = {
    "casual_chat": 0.22, "emotional_support": 0.15, "deep_reasoning": 0.25,
    "technical": 0.00, "task_help": 0.00, "crisis_support": 0.00, "celebration": 0.10,
}


def compute_prosody_params(conversation_mode: str) -> ProsodyParams:
    rate, pitch = PROSODY_TABLE.get(conversation_mode, ("medium", "+0"))
    return ProsodyParams(rate=rate, pitch=pitch)


def annotate_breaks(text: str, conversation_mode: str) -> str:
    """Insert SSML <break> tags at sentence/clause/em-dash boundaries (architecture doc §5.4)."""
    break_ms = SENTENCE_BREAK_MS.get(conversation_mode, 200)
    clause_ms = CLAUSE_BREAK_MS.get(conversation_mode, 100)
    text = re.sub(r'([.?!])\s+([A-Z])',
                  lambda m: f'{m.group(1)}<break time="{break_ms}ms"/> {m.group(2)}', text)
    text = re.sub(r',\s+(and|but|so|yet|or|because|although|however)',
                  lambda m: f',<break time="{clause_ms}ms"/> {m.group(1)}', text)
    text = text.replace(' — ', f'<break time="{clause_ms * 2}ms"/>')
    return text


def inject_fillers(text: str, conversation_mode: str, rng=_random) -> str:
    """Inject filler sounds at sentence boundaries at the per-mode rate (architecture doc §5.5)."""
    rate = FILLER_RATE.get(conversation_mode, 0.0)
    if rate == 0.0:
        return text
    sentences = text.split(". ")
    out = []
    for s in sentences:
        if s and rng.random() < rate:
            filler = rng.choice(FILLER_SOUNDS)
            s = f"{filler}, {s[0].lower()}{s[1:]}"
        out.append(s)
    return ". ".join(out)


def apply_voice_content_transforms(text: str) -> str:
    """Turn markdown/visual structure into spoken forms (architecture doc §5.6)."""
    # Bold → spoken emphasis.
    text = re.sub(r"\*\*(.+?)\*\*", r'<emphasis level="strong">\1</emphasis>', text)
    # Markdown headers → spoken transition.
    text = re.sub(r"^#{1,3}\s+(.+)$",
                  lambda m: f"On the topic of {m.group(1).lower()} —", text, flags=re.MULTILINE)
    # URLs → verbal reference.
    text = re.sub(r"https?://\S+", "I'll include a link in the text alongside this", text)

    # Bullet list → spoken enumeration.
    bullets = re.findall(r"^[-*•]\s+(.+)$", text, flags=re.MULTILINE)
    if bullets:
        ordinals = ["First", "Second", "Third", "Fourth", "Fifth"]
        spoken = "There are a few things worth noting here. " + " ".join(
            f"{ordinals[i] if i < len(ordinals) else 'And'}, {item}." for i, item in enumerate(bullets))
        text = re.sub(r"(?:^[-*•]\s+.+$\n?)+", spoken, text, flags=re.MULTILINE)
    return text


def generate_ssml(
    text: str,
    conversation_mode: str,
    circadian_band: str = "afternoon",
    relationship_stage: str = "friend",
    include_fillers: bool = False,
    apply_transforms: bool = False,
    rng=_random,
) -> SSMLDocument:
    """Assemble a complete SSML document for TTS input (architecture doc §5.2)."""
    if apply_transforms:
        text = apply_voice_content_transforms(text)
    prosody = compute_prosody_params(conversation_mode)
    annotated = annotate_breaks(text, conversation_mode)
    if include_fillers:
        annotated = inject_fillers(annotated, conversation_mode, rng)
    ssml = (f'<speak>\n  <prosody rate="{prosody.rate}" pitch="{prosody.pitch}st">\n'
            f'    {annotated}\n  </prosody>\n</speak>')
    return SSMLDocument(ssml=ssml, prosody=prosody, fillers_included=include_fillers)


def synthesize(
    text: str,
    backend,
    conversation_mode: str,
    circadian_band: str = "afternoon",
    relationship_stage: str = "friend",
    include_fillers: bool = False,
    apply_transforms: bool = False,
    voice_id: Optional[str] = None,
    rng=_random,
) -> AudioResult:
    """Generate SSML and dispatch to the TTS backend; degrade to non-ok on failure (§9)."""
    if backend is None:
        return AudioResult(ok=False, error="no TTS backend configured")
    doc = generate_ssml(text, conversation_mode, circadian_band, relationship_stage,
                        include_fillers, apply_transforms, rng)
    try:
        return backend.synthesize(doc.ssml, voice_id=voice_id)
    except Exception as exc:
        return AudioResult(ok=False, error=f"tts synthesis failed: {exc}")
