"""Sync routes — Layer 12 zero-knowledge cross-device sync (single-user, multi-device).

The server is a blind relay: it stores opaque AES ciphertext produced on-device by
``SyncCoordinator.build_delta`` and hands each device the deltas from *other* devices past its
cursor. It never holds the key and never decrypts. See ``infra/db/sync_store.py``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import (SyncDeltaIn, SyncDeltaOut, SyncPullOut, SyncPushOut, SyncStatusOut)
from infra.db.sync_store import PostgresSyncStore

router = APIRouter(prefix="/sync", tags=["sync"])


def _store(state):
    return PostgresSyncStore(state.session_factory, state.default_user_id)


@router.post("/push", response_model=SyncPushOut, status_code=201)
def sync_push(delta: SyncDeltaIn, state=Depends(get_state)):
    try:
        stored = _store(state).push(delta.delta_id, delta.source_device, delta.seq,
                                    delta.encrypted_payload, delta.size_bytes)
    except Exception:
        raise HTTPException(status_code=503, detail="sync temporarily unavailable")
    return SyncPushOut(stored=stored, delta_id=delta.delta_id)


@router.get("/pull", response_model=SyncPullOut)
def sync_pull(device_id: str, after: int = 0, state=Depends(get_state)):
    try:
        deltas, cursor = _store(state).pull(device_id, after)
    except Exception:
        raise HTTPException(status_code=503, detail="sync temporarily unavailable")
    return SyncPullOut(deltas=[SyncDeltaOut(**d) for d in deltas], cursor=cursor)


@router.get("/status", response_model=SyncStatusOut)
def sync_status(state=Depends(get_state)):
    try:
        return SyncStatusOut(**_store(state).status())
    except Exception:
        raise HTTPException(status_code=503, detail="sync temporarily unavailable")
