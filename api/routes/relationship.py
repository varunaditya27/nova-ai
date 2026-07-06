"""Relationship route — read the per-user Layer-4/5 relationship state (single-user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import RelationshipOut
from infra.db.relationship_store import PostgresRelationshipStore

router = APIRouter(prefix="/relationship", tags=["relationship"])


@router.get("", response_model=RelationshipOut)
def get_relationship(state=Depends(get_state)):
    try:
        rel = PostgresRelationshipStore(state.session_factory, state.default_user_id).load()
    except Exception:
        raise HTTPException(status_code=503, detail="relationship state unavailable")
    return RelationshipOut(
        stage=rel.stage, total_sessions=rel.total_sessions,
        total_messages_exchanged=rel.total_messages_exchanged,
        tie_strength=getattr(rel, "tie_strength", 0.0),
        trust_score=getattr(rel, "trust_score", 0.0))
