"""SocialGraph-specific JSON codec.

``infra.db.memory_serde``'s generic ``to_jsonable``/``from_jsonable`` only recurses into
dataclass fields, lists, and (for value reconstruction) has no support for a bare, untyped
``dict`` field whose values are themselves dataclasses -- exactly the shape of
``SocialGraph.nodes`` (``person_id -> SocialNode``) and ``SocialGraph.edges`` (a ``(a, b)``
tuple key -> ``SocialEdge``, and JSON has no tuple keys at all). Rather than teaching the
shared generic codec a new, single-caller shape, this module reuses it at the leaf level
(``SocialNode``/``SocialEdge`` are plain dataclasses with only scalar/list/datetime fields)
and handles the two container fields explicitly.
"""
from __future__ import annotations

from datetime import datetime

from backend.layer5_relationship.schemas import SocialEdge, SocialGraph, SocialNode
from infra.db.memory_serde import from_jsonable, to_jsonable

_EDGE_KEY_SEP = "\x1f"   # not a legal character in a person_id (uuid4 str)


def graph_to_jsonable(graph: SocialGraph) -> dict:
    return {
        "user_id": graph.user_id,
        "nodes": {pid: to_jsonable(node) for pid, node in graph.nodes.items()},
        "edges": {
            _EDGE_KEY_SEP.join(key): to_jsonable(edge) for key, edge in graph.edges.items()
        },
        "last_updated": to_jsonable(graph.last_updated),
        "version": graph.version,
    }


def graph_from_jsonable(data: dict) -> SocialGraph:
    last_updated = data.get("last_updated")
    return SocialGraph(
        user_id=data.get("user_id", ""),
        nodes={pid: from_jsonable(SocialNode, node) for pid, node in data.get("nodes", {}).items()},
        edges={
            tuple(key.split(_EDGE_KEY_SEP)): from_jsonable(SocialEdge, edge)
            for key, edge in data.get("edges", {}).items()
        },
        last_updated=datetime.fromisoformat(last_updated) if last_updated else None,
        version=data.get("version", 0),
    )
