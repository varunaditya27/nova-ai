"""SC-4 — Cross-Platform Sync (architecture doc §6).

Resolves the sync tension by making the user hold the key: data travels through Nova's
infrastructure as opaque AES ciphertext the server cannot read. ``build_delta`` encrypts the
operations payload on-device (server sees only ciphertext + routing metadata); ``decrypt_delta``
reverses it on another device with the same sync key. ``resolve_conflict`` applies per-memory-type
policy when two devices edit the same record offline (episodic → insert; semantic → last-write-wins;
identity → hold for the user; personality → weighted merge; longitudinal → keep the more complete).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Optional

from backend.layer12_privacy import encryption_manager as em
from backend.layer12_privacy.schemas import ResolvedOperation, SyncDelta, SyncOperation


def _hash_device(device_id: str) -> str:
    return hashlib.sha256(device_id.encode("utf-8")).hexdigest()[:16]


def _op_to_dict(op: SyncOperation) -> dict:
    return {"operation_type": op.operation_type, "record_id": op.record_id,
            "store_name": op.store_name, "serialized_record": op.serialized_record,
            "timestamp": op.timestamp.isoformat() if isinstance(op.timestamp, datetime)
            else op.timestamp}


class SyncCoordinator:
    def __init__(self, user_id: str, device_id: str, sync_key: bytes) -> None:
        self.user_id = user_id
        self.device_id = device_id
        self.sync_key = sync_key
        self._sequence = 0

    def build_delta(self, operations: list, now: Optional[datetime] = None) -> SyncDelta:
        """Package and encrypt local changes into a delta (architecture doc §6.3)."""
        self._sequence += 1
        plaintext = json.dumps([_op_to_dict(o) for o in operations], default=str)
        token = em.encrypt(plaintext, self.sync_key)
        return SyncDelta(
            user_id=self.user_id, source_device_id=_hash_device(self.device_id),
            created_at=now or datetime.utcnow(), sequence_number=self._sequence,
            encrypted_payload=token, payload_size_bytes=len(token))

    def decrypt_delta(self, delta: SyncDelta) -> list:
        """Decrypt a delta locally back into SyncOperations (architecture doc §6.3)."""
        plaintext = em.decrypt(delta.encrypted_payload, self.sync_key).decode("utf-8")
        return [SyncOperation(operation_type=d["operation_type"], record_id=d["record_id"],
                              store_name=d["store_name"], serialized_record=d["serialized_record"],
                              timestamp=d.get("timestamp")) for d in json.loads(plaintext)]


def _get(record, key, default=None):
    if record is None:
        return default
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def resolve_conflict(op_from_remote: SyncOperation, local_record) -> ResolvedOperation:
    """Per-memory-type conflict resolution (architecture doc §6.4)."""
    store = op_from_remote.store_name
    remote = op_from_remote.serialized_record

    # Episodic: a new memory from another device simply inserts; no conflict possible.
    if store == "episodic_memories":
        return ResolvedOperation(action="insert", record=remote)

    if local_record is None:
        return ResolvedOperation(action="insert", record=remote)

    # Semantic: last-write-wins with notification.
    if store == "semantic_facts":
        if _get(remote, "last_updated_at", "") > _get(local_record, "last_updated_at", ""):
            return ResolvedOperation(action="overwrite", record=remote,
                                     notify="A fact was updated on another device.")
        return ResolvedOperation(action="keep_local")

    # Identity: requires explicit user resolution when content differs.
    if store == "identity_beliefs":
        if _get(remote, "content") != _get(local_record, "content"):
            return ResolvedOperation(action="hold_pending_user_resolution", record=remote)
        return ResolvedOperation(action="keep_local")

    # Personality vector: component-wise merge weighted by interaction count.
    if store == "personality_vector":
        lw = _get(local_record, "interaction_count", 0)
        rw = _get(remote, "interaction_count", 0)
        local_traits = _get(local_record, "traits", {}) or {}
        remote_traits = _get(remote, "traits", {}) or {}
        total = lw + rw
        merged = {}
        for name, lval in local_traits.items():
            rval = remote_traits.get(name, lval)
            merged[name] = (lval * lw + rval * rw) / total if total else (lval + rval) / 2
        return ResolvedOperation(action="overwrite",
                                 record={"traits": merged, "interaction_count": total})

    # Longitudinal: keep the more complete narrative.
    if store in ("weekly_summaries", "life_chapters", "retrospective_packets"):
        if len(_get(remote, "narrative_summary", "") or "") > \
                len(_get(local_record, "narrative_summary", "") or ""):
            return ResolvedOperation(action="overwrite", record=remote,
                                     notify="The more complete version was kept.")
        return ResolvedOperation(action="keep_local")

    # All other: last-write-wins.
    if _get(remote, "updated_at", "") > _get(local_record, "updated_at", ""):
        return ResolvedOperation(action="overwrite", record=remote)
    return ResolvedOperation(action="keep_local")
