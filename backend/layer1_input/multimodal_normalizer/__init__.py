"""Layer 1 · Sub-Component 3 — Multimodal Normalizer (architecture doc §5).

Heavy model calls — vision (LLaVA / GPT-4o), transcription (Whisper.cpp), document extraction
(Apache Tika) — sit behind injectable backend Protocols (``types.py``). Deterministic
modalities (reaction, location) need no backend (``deterministic.py``). Backend-invoking
normalizers live in ``backend_normalizers.py``; ``core.py`` dispatches per attachment type
and assembles the final ``ModalityContext``.
"""

from __future__ import annotations

from .core import normalize
from .deterministic import REACTION_EMOJI_MAP, map_reaction
from .types import (
    DocumentBackend,
    ImageBackend,
    ImageResult,
    NormalizerBackends,
    VoiceBackend,
    VoiceTranscript,
)

__all__ = [
    "REACTION_EMOJI_MAP",
    "DocumentBackend",
    "ImageBackend",
    "ImageResult",
    "NormalizerBackends",
    "VoiceBackend",
    "VoiceTranscript",
    "map_reaction",
    "normalize",
]
