"""Layer 2 memory type classes (re-exported from :mod:`schemas`).

The five memory types of the architecture doc live in ``schemas`` as the single source of
truth. This module re-exports them for callers that import by the conventional name.

Note: the architecture defines five types as Short-Term buffer, Episodic, Semantic, Identity,
and the User World Model. The earlier scaffold's "ProceduralMemory" is not part of the spec —
communication/behavioral patterns are modelled in the UWM's communication/psychological models
and as SemanticMemory entries.
"""

from .schemas import (  # noqa: F401
    EpisodicMemory,
    IdentityMemory,
    SemanticMemory,
    ShortTermMemoryBuffer,
    UserWorldModel,
)

__all__ = [
    "ShortTermMemoryBuffer",
    "EpisodicMemory",
    "SemanticMemory",
    "IdentityMemory",
    "UserWorldModel",
]
