# Layer 12 — Privacy & Data
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

Every layer built before this one rests on a single implicit assumption: the user trusts Nova enough to be honest with it. That trust is not free. It is earned — through consistent warmth and memory, yes — but more fundamentally through the knowledge that what the user shares is safe, that they retain sovereignty over their own data, and that the system cannot be used against them.

Layer 12 is the architecture of that trust. It is not a compliance wrapper. It is the engineering that makes the promise of a private, personal AI companion credible in practice.

The central challenge Layer 12 resolves is a genuine tension: **better personalization requires richer data retention; better privacy requires less of it.** NovaAI's architecture does not resolve this tension by sacrificing one goal for the other. It resolves it through on-device processing, zero-knowledge encryption, user-controlled key material, granular deletion, and full transparency — so the user can give Nova deep access to their inner life precisely because they know they can take it back at any time.

Layer 12 contains **four sub-components**:

- **SC-1: On-Device Memory** — where data lives, how it is encrypted, and who can reach it
- **SC-2: Selective Deletion** — what the user can make Nova forget, and how completely, including cascade handling
- **SC-3: Memory Audit** — what Nova actually knows, made transparent, queryable, correctable, and inspectable
- **SC-4: Cross-Platform Sync** — how the experience moves across devices without compromising any of the above

All four are coordinated by a persistent **Privacy Agent** that runs as a background service on the user's device.

---

## 2. Architecture Overview

```
User's Device (Primary)
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  /nova-data/ (encrypted at rest; all files SQLCipher or AES-256-GCM) │  │
│  │                                                                      │  │
│  │  memory.db           episodic + semantic + identity (SQLCipher)     │  │
│  │  memory.vdb          vector embeddings (hnswlib, AES-256-GCM)       │  │
│  │  longitudinal.db     Layer 10 data (SQLCipher)                      │  │
│  │  personality.db      personality vector + drift history (SQLCipher)  │  │
│  │  goals.db            Layer 7 goal state (SQLCipher)                 │  │
│  │  safety.db           Layer 11 safety record (SQLCipher)             │  │
│  │  audit.db            audit index + deletion log (SQLCipher)         │  │
│  │  keystore/           hardware-bound key material (Secure Enclave)   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                        ▲                                                    │
│                        │ read/write (all in-process, no network)            │
│                        │                                                    │
│  ┌─────────────────────┴────────────────────────────────────────────────┐  │
│  │  Privacy Agent (persistent background service)                       │  │
│  │                                                                      │  │
│  │  EncryptionManager    DeletionExecutor    AuditIndexBuilder          │  │
│  │  SyncCoordinator      IntegrityVerifier   ConsentManager             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                        │                                                    │
│          E2E-encrypted sync deltas only (no plaintext ever leaves device)  │
└──────────────────────────────────────────────────────────────────────────── ┘
                          │
                          ▼
              Nova Sync Server
              ┌──────────────────────────────────────┐
              │  Encrypted Blob Store                │
              │  (opaque AES-256-GCM ciphertext)     │
              │                                      │
              │  server sees: account_id, blob_size, │
              │    sync_timestamp                    │
              │  server NEVER sees: key, plaintext,  │
              │    content, user identity data       │
              └──────────────────────────────────────┘
                          │
                          ▼
              User's Device (Secondary — laptop, tablet, etc.)
              ┌──────────────────────────────────────┐
              │  Decrypts with user's key (local)    │
              │  Populates local /nova-data/          │
              └──────────────────────────────────────┘
```

**Fundamental rule:** Anything that contains, or could be used to reconstruct, conversation content stays on device. The cloud never sees plaintext, even in encrypted form that Nova holds the key to, unless the user has opted in to cloud backup and holds the only decryption key.

---

## 3. Sub-Component 1 — On-Device Memory

### 3.1 Storage Location Decision — The Hybrid Tiered Model

| Memory Type | Storage Location | Rationale |
|---|---|---|
| Short-term buffer (current session) | Device RAM only | Session-scoped; never written to disk |
| Episodic memory summaries | Local encrypted store (`memory.db`) | Highest sensitivity — personal events |
| Episodic embeddings | Local encrypted vector store (`memory.vdb`) | Embedding-based retrieval; personally identifying |
| Semantic memory (facts, preferences) | Local encrypted store (`memory.db`) | Personally identifying inferences |
| Identity memory (beliefs, values) | Local encrypted store, protected partition (`memory.db`) | Most sensitive — core self-model |
| Personality vector + drift history | Local encrypted store (`personality.db`) | Behavioral fingerprint |
| Layer 7 goal state | Local encrypted store (`goals.db`) | Personal ambitions and plans |
| Layer 10 longitudinal data | Local encrypted store (`longitudinal.db`) | Intimate life arc; separate file for independent deletion |
| Layer 11 safety record | Local encrypted store (`safety.db`) | Metadata only; no content |
| Aggregate usage telemetry | Optional cloud (anonymized, opt-in only) | No content; behavioral aggregates only |

### 3.2 Encryption Architecture

```python
class KeyHierarchy:
    """
    The complete key hierarchy for NovaAI on-device storage.
    All keys are derived; none are stored in plaintext anywhere.
    """

    # ── MASTER KEY ─────────────────────────────────────────────────────────────
    # Derived from user passphrase + device hardware key.
    # Never leaves the device.
    # Never accessible to Nova servers.
    # Stored in: iOS Secure Enclave / Android Keystore / Windows TPM / macOS Secure Enclave.
    master_key: bytes       # AES-256-GCM
    # Derivation: PBKDF2-HMAC-SHA256(passphrase, device_hardware_salt, iterations=600_000)
    # The device_hardware_salt is generated once per device and stored in the
    # OS secure storage facility — it cannot be extracted from the device.

    # ── MEMORY ENCRYPTION KEY ──────────────────────────────────────────────────
    # Used to encrypt all persistent memory stores on disk.
    memory_encryption_key: bytes    # AES-256-GCM
    # Derivation: HKDF(master_key, salt=memory_key_derivation_salt, info=b"memory_enc")
    # Rotation: every 90 days OR on user explicit request.
    # On rotation: all stores re-encrypted with new key; old key securely zeroed.

    # ── VECTOR STORE KEY ───────────────────────────────────────────────────────
    # Separate key for the vector store to allow independent access control.
    vector_encryption_key: bytes    # AES-256-GCM
    # Derivation: HKDF(master_key, salt=vector_key_derivation_salt, info=b"vector_enc")

    # ── SESSION KEY ────────────────────────────────────────────────────────────
    # Ephemeral; derived fresh for each conversation session.
    # Used only for in-memory pipeline data; never written to disk.
    # Lifespan: single session only.
    session_key: bytes      # AES-256-GCM
    # Derivation: HKDF(master_key, salt=session_timestamp_bytes, info=b"session_enc")

    # ── SYNC KEY ───────────────────────────────────────────────────────────────
    # User-controlled key for optional encrypted cloud backup.
    # Derived from user passphrase using a separate high-iteration KDF.
    # Nova servers NEVER hold this key or any derivative of it.
    sync_backup_key: bytes  # AES-256-GCM
    # Derivation: Argon2id(passphrase, sync_salt, time_cost=4, memory_cost=65536)
    # The sync_salt is stored locally in the device keystore.
    # On a new device: user enters passphrase → sync_salt fetched from server
    # (the salt itself is not sensitive) → sync_backup_key rederived locally.

class KeyLifecycleManager:
    """Manages key creation, rotation, and secure destruction."""

    def initialize_keys(self, passphrase: str, device_id: str) -> None:
        """Called once on first installation."""
        device_hardware_salt = self._generate_and_store_hardware_salt(device_id)
        master_key = pbkdf2_hmac_sha256(passphrase, device_hardware_salt, iterations=600_000)
        memory_enc_key = hkdf(master_key, salt=os.urandom(32), info=b"memory_enc")
        vector_enc_key = hkdf(master_key, salt=os.urandom(32), info=b"vector_enc")
        self._store_keys_in_secure_enclave(master_key, memory_enc_key, vector_enc_key)
        # Note: master_key itself is never stored to disk — it is rederived from
        # passphrase + hardware_salt on every app launch.

    def rotate_memory_encryption_key(self) -> None:
        """Rotates the memory encryption key. Re-encrypts all stores."""
        old_key = self._retrieve_memory_enc_key()
        new_key = hkdf(self._retrieve_master_key(), salt=os.urandom(32), info=b"memory_enc")
        self._reencrypt_all_stores(old_key, new_key)
        self._store_new_memory_enc_key(new_key)
        self._secure_zero(old_key)

    def derive_session_key(self, session_start_timestamp: float) -> bytes:
        """Derives a fresh session key for the current conversation."""
        return hkdf(
            self._retrieve_master_key(),
            salt=struct.pack(">d", session_start_timestamp),
            info=b"session_enc"
        )

    def destroy_all_keys(self) -> None:
        """Called on full data wipe. Securely zeros all key material."""
        for key_name in ["master_key", "memory_enc_key", "vector_enc_key", "sync_backup_key"]:
            self._secure_zero_from_enclave(key_name)
```

### 3.3 Physical Store Architecture

```python
STORE_ARCHITECTURE = {
    "memory.db": {
        "type": "SQLite with SQLCipher",
        "encryption": "AES-256-GCM via SQLCipher 4.x",
        "key": "memory_encryption_key",
        "tables": [
            "episodic_memories",        # all episodic memory entries
            "semantic_facts",           # all extracted stable facts
            "identity_beliefs",         # identity memory entries
            "memory_reinforcements",    # reinforcement event log
            "consolidation_log",        # consolidation operations history
        ],
        "rationale": "Relational structure; all metadata, importance scores, "
                     "timestamps, emotional weights, topic tags."
    },
    "memory.vdb": {
        "type": "hnswlib index (local mode)",
        "encryption": "AES-256-GCM wrapping at file level",
        "key": "vector_encryption_key",
        "contents": [
            "episodic_memory_embeddings",   # 384-dim vectors (all-MiniLM-L6-v2)
            "semantic_fact_embeddings",     # same embedding model
        ],
        "index_params": {
            "space": "cosine",
            "ef_construction": 200,
            "M": 16,
            "max_elements": 100_000,        # sufficient for ~5 years of daily use
        },
        "rationale": "Embedding-based similarity retrieval for Layer 2 recall scoring. "
                     "hnswlib runs entirely in-process — no server, no network."
    },
    "longitudinal.db": {
        "type": "SQLite with SQLCipher",
        "encryption": "AES-256-GCM via SQLCipher",
        "key": "memory_encryption_key",
        "tables": [
            "life_chapters",
            "narrative_moments",
            "weekly_summaries",
            "progress_records",
            "behavioral_patterns",
            "retrospective_packets",
            "life_calendar_entries",
        ],
        "rationale": "Separate file from memory.db — enables independent backup, "
                     "independent deletion, and architectural separation of Layer 10 data."
    },
    "personality.db": {
        "type": "SQLite with SQLCipher",
        "encryption": "AES-256-GCM via SQLCipher",
        "key": "memory_encryption_key",
        "tables": [
            "personality_vector_current",
            "personality_vector_history",   # snapshots with timestamps
            "style_learning_parameters",
            "drift_event_log",
        ],
        "rationale": "Separate from memory.db — personality data has a different "
                     "update cadence and access pattern."
    },
    "goals.db": {
        "type": "SQLite with SQLCipher",
        "encryption": "AES-256-GCM via SQLCipher",
        "key": "memory_encryption_key",
        "tables": [
            "goal_objects",
            "goal_steps",
            "life_events",
            "pending_threads",
            "task_completion_log",
        ],
        "rationale": "Layer 7 data kept separate — different deletion semantics "
                     "(completed goals are not automatically deleted)."
    },
    "safety.db": {
        "type": "SQLite with SQLCipher",
        "encryption": "AES-256-GCM via SQLCipher; additional integrity protection",
        "key": "memory_encryption_key",
        "tables": [
            "safety_record_entries",        # tamper-evident chain (Layer 11)
        ],
        "note": "User CANNOT delete safety.db contents. "
                "Contents are metadata only — no conversation text."
    },
    "audit.db": {
        "type": "SQLite with SQLCipher",
        "encryption": "AES-256-GCM via SQLCipher",
        "key": "memory_encryption_key",
        "tables": [
            "audit_index",                  # fast-lookup index for Memory Audit queries
            "deletion_log",                 # all deletion events with certificates
            "provenance_records",           # memory → source session tracing
            "consent_records",              # user privacy preferences with timestamps
            "integrity_checksums",          # Merkle tree hashes for tamper detection
        ],
    },
}
```

### 3.4 Integrity Verification

```python
class IntegrityVerifier:
    """
    Runs daily. Detects unauthorized modification of memory store files.
    Uses a Merkle tree of store contents, anchored in a separate
    hardware-protected checksum.
    """

    def compute_store_merkle_root(self) -> bytes:
        """Compute the Merkle root hash of all memory store content."""
        # Leaf nodes: SHA-256 of each record in each table
        leaf_hashes = []
        for store_name, store_config in STORE_ARCHITECTURE.items():
            if store_name == "safety.db":
                continue    # safety.db has its own separate chain in Layer 11
            records = self._read_all_records(store_name)
            for record in records:
                leaf_hashes.append(sha256(serialize(record)))

        # Build Merkle tree and return root
        return build_merkle_tree(leaf_hashes).root

    def run_daily_check(self) -> IntegrityCheckResult:
        """Compare today's Merkle root against yesterday's stored root."""
        current_root = self.compute_store_merkle_root()
        stored_root = self._retrieve_stored_root_from_enclave()
        expected_root = self._recompute_expected_root(
            previous_root=stored_root,
            recorded_writes=self._get_write_log_since_last_check(),
            recorded_deletions=self._get_deletion_log_since_last_check(),
        )

        if current_root != expected_root:
            # Mismatch beyond expected writes and deletions
            self._alert_user_of_potential_tampering(
                current_root=current_root,
                expected_root=expected_root,
            )
            return IntegrityCheckResult(status="TAMPER_DETECTED", details=...)

        # Update stored root for next check
        self._store_root_in_enclave(current_root)
        return IntegrityCheckResult(status="INTACT")

class IntegrityCheckResult:
    status: Literal["INTACT", "TAMPER_DETECTED", "CHECK_FAILED"]
    checked_at: datetime
    current_root: bytes
    expected_root: bytes
    mismatch_details: Optional[str]
```

---

## 4. Sub-Component 2 — Selective Deletion

### 4.1 Deletion Taxonomy

Not all deletion requests are the same. The system handles six distinct types with appropriate precision and different undo windows.

```python
class DeletionType(str, Enum):
    SINGLE_MEMORY       = "single_memory"       # one specific episodic memory
    TOPIC_BASED         = "topic_based"         # everything about a topic/person/period
    SEMANTIC_WIPE       = "semantic_wipe"       # a specific semantic fact or cluster
    IDENTITY_MEMORY     = "identity_memory"     # a belief, value, or trait from identity store
    LONGITUDINAL_DATA   = "longitudinal_data"   # a chapter, weekly summary, or retrospective
    FULL_WIPE           = "full_wipe"           # complete deletion of all user data

DELETION_UNDO_WINDOWS = {
    DeletionType.SINGLE_MEMORY:     timedelta(hours=1),
    DeletionType.TOPIC_BASED:       timedelta(hours=1),
    DeletionType.SEMANTIC_WIPE:     timedelta(hours=1),
    DeletionType.IDENTITY_MEMORY:   timedelta(hours=24),    # longest window — hardest to rebuild
    DeletionType.LONGITUDINAL_DATA: timedelta(hours=1),
    DeletionType.FULL_WIPE:         timedelta(0),           # irreversible; no undo window
}

DELETION_CONFIRMATION_REQUIREMENTS = {
    DeletionType.SINGLE_MEMORY:     "standard",             # tap delete + confirm
    DeletionType.TOPIC_BASED:       "review_then_confirm",  # review scope, then confirm
    DeletionType.SEMANTIC_WIPE:     "standard",
    DeletionType.IDENTITY_MEMORY:   "extra",                # extra confirmation step + type "DELETE"
    DeletionType.LONGITUDINAL_DATA: "review_then_confirm",
    DeletionType.FULL_WIPE:         "extra_plus_passphrase", # requires passphrase re-entry
}
```

### 4.2 Deletion Request Schema

```python
class DeletionScope:
    """Defines exactly what is to be deleted."""
    # For SINGLE_MEMORY
    memory_id: Optional[UUID]

    # For TOPIC_BASED
    topic_tags: Optional[list[str]]         # e.g., ["relationships", "arjun"]
    person_name: Optional[str]              # e.g., "Arjun"
    date_range: Optional[tuple[date, date]] # e.g., (date(2025,3,1), date(2025,6,30))

    # For SEMANTIC_WIPE
    semantic_fact_ids: Optional[list[UUID]]

    # For IDENTITY_MEMORY
    identity_entry_ids: Optional[list[UUID]]

    # For LONGITUDINAL_DATA
    chapter_ids: Optional[list[UUID]]

    # For FULL_WIPE
    full_wipe_confirmed: bool = False
```

**As-built (§14 2026-08-12):** `date_range` is real and wired (narrows `resolve_scope`'s
TOPIC_BASED branch by `created_at`). `semantic_category`, `identity_category`,
`weekly_summary_ids`, and `retrospective_ids` were removed — none of the four were ever
implemented in code at all (doc/code had simply diverged, not a wiring gap); reintroduce any of
them if a real caller needs that narrowing.

```python
class DeletionRequest:
    request_id: UUID
    user_id: str
    requested_at: datetime
    deletion_type: DeletionType
    scope: DeletionScope
    confirmation_required: str
    undo_window_expiry: datetime
    status: Literal["pending", "scope_resolved", "awaiting_confirmation",
                    "confirmed", "executing", "complete", "undone", "expired"]

    # Populated after dry run
    affected_memory_ids: list[UUID]
    cascade_impacts: CascadeImpactReport
    dry_run_completed: bool

    # Populated after execution
    deletion_certificate: Optional[str]     # cryptographic proof of completion
    executed_at: Optional[datetime]

class CascadeImpactReport:
    """What will change if this deletion is executed."""
    memories_deleted: int
    semantic_facts_affected: list[tuple[UUID, str, str]]    # (id, fact_text, impact_type)
    # impact_type: "will_be_deleted" | "will_be_updated" | "will_be_flagged_for_review"
    personality_vector_will_change: bool
    personality_params_affected: list[str]                   # e.g., ["verbosity", "empathy_level"]
    longitudinal_references_to_update: list[tuple[UUID, str]] # (summary_id, description)
    summary_human_readable: str                             # presented to user before confirmation
```

**As-built (§14 2026-08-12):** `chapters_affected`/`chapter_merge_required` were removed from the
real `CascadeImpactReport` — `dry_run_deletion` only wires 3 cascade store types today (semantic,
personality, longitudinal-summary); a 4th chapter/narrative-arc cascade store was never added as an
injectable param, so this pseudocode's chapter-merge algorithm below was never connected to a real
caller. Reintroduce both together if a real chapter-cascade store is added.

### 4.3 Deletion Execution Algorithm

```python
class DeletionExecutor:

    def execute_deletion(self, request: DeletionRequest) -> DeletionCertificate:
        """
        Execute a confirmed deletion request with full cascade handling.
        All operations are atomic within a database transaction.
        """
        assert request.status == "confirmed"
        assert request.dry_run_completed

        with database_transaction() as txn:
            deleted_ids = []

            # Step 1: Resolve all memory IDs to delete
            target_ids = self._resolve_scope(request.scope, request.deletion_type)

            # Step 2: Secure delete from vector store
            for memory_id in target_ids:
                if has_embedding(memory_id):
                    self._secure_zero_embedding(memory_id)
                    vector_store.remove(memory_id)
                    deleted_ids.append(memory_id)

            # Step 3: Secure delete from structured store
            for memory_id in target_ids:
                record = memory_db.get(memory_id)
                if record:
                    # Overwrite content and embedding fields with zeros before delete
                    memory_db.update(memory_id, {
                        "content": b"\x00" * len(record.content),
                        "embedding": None,
                        "emotional_weight": 0.0,
                        "importance_score": 0.0,
                    })
                    memory_db.delete(memory_id)

            # Step 4: Handle cascade impacts
            for fact_id, fact_text, impact_type in request.cascade_impacts.semantic_facts_affected:
                if impact_type == "will_be_deleted":
                    self._delete_semantic_fact(fact_id, txn)
                elif impact_type == "will_be_updated":
                    self._recompute_semantic_fact_from_remaining_episodes(fact_id, txn)

            # Step 5: Recompute personality vector if affected
            if request.cascade_impacts.personality_vector_will_change:
                self._recompute_personality_vector_from_remaining_data(txn)

            # Step 6: Update longitudinal references
            for summary_id, description in request.cascade_impacts.longitudinal_references_to_update:
                self._remove_reference_from_summary(summary_id, memory_ids=target_ids, txn=txn)

            # Step 7: Handle chapter merges if needed
            if request.cascade_impacts.chapter_merge_required:
                self._merge_underpopulated_chapters(
                    affected_chapters=request.cascade_impacts.chapters_affected,
                    txn=txn
                )

            txn.commit()

        # Step 8: Generate deletion certificate
        certificate = self._generate_deletion_certificate(
            deleted_ids=deleted_ids,
            request_id=request.request_id,
            executed_at=datetime.utcnow(),
        )

        # Step 9: Record in deletion log
        audit_db.insert_deletion_log_entry(
            request_id=request.request_id,
            deletion_type=request.deletion_type,
            memory_count=len(deleted_ids),
            certificate=certificate,
            executed_at=datetime.utcnow(),
        )

        return certificate

    def _secure_zero_embedding(self, memory_id: UUID) -> None:
        """Overwrite embedding with zeros before removal. Prevents forensic recovery."""
        embedding = vector_store.get_embedding(memory_id)
        if embedding:
            # Overwrite with zeros in-memory before removal
            ctypes.memset(embedding.ctypes.data, 0, embedding.nbytes)
        vector_store.remove(memory_id)

    def _generate_deletion_certificate(
        self,
        deleted_ids: list[UUID],
        request_id: UUID,
        executed_at: datetime,
    ) -> str:
        """
        Generate a cryptographic certificate of deletion completion.
        Signed with the device key stored in the Secure Enclave.
        """
        payload = {
            "request_id": str(request_id),
            "deleted_ids": [str(id) for id in deleted_ids],
            "deleted_count": len(deleted_ids),
            "executed_at": executed_at.isoformat(),
        }
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        payload_hash = sha256(payload_bytes).hexdigest()
        device_signature = secure_enclave_sign(payload_hash)
        return base64.b64encode(
            json.dumps({
                "payload_hash": payload_hash,
                "device_signature": device_signature,
                "timestamp": executed_at.isoformat(),
            }).encode()
        ).decode()
```

### 4.4 Dry Run — Pre-Execution Scope Preview

```python
def dry_run_deletion(
    request: DeletionRequest,
    memory_store: MemoryStore,
    longitudinal_store: LongitudinalStore,
    personality_store: PersonalityStore,
) -> CascadeImpactReport:
    """
    Compute the full set of changes that would result from this deletion
    WITHOUT executing any of them.
    Presented to the user before they confirm.
    """

    # Step 1: Resolve target memory IDs
    target_ids = resolve_deletion_scope(request.scope, request.deletion_type, memory_store)

    # Step 2: Find semantic facts that cite these memories as primary source
    affected_facts = []
    for fact in semantic_store.get_all():
        citing_episodes = [ep_id for ep_id in fact.derived_from_episodes if ep_id in target_ids]
        if not citing_episodes:
            continue
        non_cited_episodes = [ep_id for ep_id in fact.derived_from_episodes if ep_id not in target_ids]
        if len(non_cited_episodes) == 0:
            affected_facts.append((fact.fact_id, fact.fact_text, "will_be_deleted"))
        elif len(non_cited_episodes) < 2:
            affected_facts.append((fact.fact_id, fact.fact_text, "will_be_updated"))
        else:
            affected_facts.append((fact.fact_id, fact.fact_text, "will_be_flagged_for_review"))

    # Step 3: Check personality vector impact
    personality_impact = personality_store.simulate_removal_impact(target_ids)
    pv_will_change = personality_impact.max_delta > 0.05  # >5% change in any trait

    # Step 4: Find longitudinal references
    longitudinal_refs = []
    for summary in longitudinal_store.get_all_weekly_summaries():
        referenced_ids = [eid for eid in summary.backing_episode_ids if eid in target_ids]
        if referenced_ids:
            longitudinal_refs.append((summary.summary_id,
                                       f"Week of {summary.week_start_date}: "
                                       f"{len(referenced_ids)} reference(s) would be removed"))

    # Step 5: Check chapter integrity
    chapters_affected = []
    merge_required = False
    for chapter in longitudinal_store.get_all_chapters():
        affected_moments = [m for m in chapter.defining_moments if m.episode_ids[0] in target_ids]
        if affected_moments:
            chapters_affected.append((chapter.chapter_id, chapter.title))
            remaining_moments = len(chapter.defining_moments) - len(affected_moments)
            if remaining_moments < 1:
                merge_required = True

    # Step 6: Human-readable summary
    summary_lines = [f"Deleting {len(target_ids)} memory/memories will also:"]
    if affected_facts:
        del_count = sum(1 for _, _, t in affected_facts if t == "will_be_deleted")
        if del_count:
            summary_lines.append(f"  • Remove {del_count} inferred fact(s) derived exclusively from these memories")
    if pv_will_change:
        summary_lines.append(f"  • Recalculate your personality profile (up to {personality_impact.max_delta:.0%} change)")
    if longitudinal_refs:
        summary_lines.append(f"  • Update {len(longitudinal_refs)} weekly summary/summaries")
    if merge_required:
        summary_lines.append(f"  • Ask you about merging an underpopulated chapter")

    return CascadeImpactReport(
        memories_deleted=len(target_ids),
        semantic_facts_affected=affected_facts,
        personality_vector_will_change=pv_will_change,
        personality_params_affected=personality_impact.affected_params,
        longitudinal_references_to_update=longitudinal_refs,
        chapters_affected=chapters_affected,
        chapter_merge_required=merge_required,
        summary_human_readable="\n".join(summary_lines),
    )
```

---

## 5. Sub-Component 3 — Memory Audit

### 5.1 Purpose and Design Principle

The Memory Audit is the **transparency interface** — a complete, human-readable, queryable, and correctable view of everything Nova knows about the user. Without a Memory Audit, privacy is a claim. With one, it is a verifiable property.

The design principle: the Memory Audit should be the most trust-building feature in the entire product. A user who opens it and sees exactly what Nova knows — no more, no less, clearly organized, with the ability to query, correct, anchor, expire, or delete anything they see — will trust Nova with more than a user who takes the privacy promise on faith.

### 5.2 Memory Audit View Schema

```python
class MemoryAuditView:
    user_id: str
    generated_at: datetime
    total_memory_count: int
    total_storage_size_bytes: int
    oldest_memory_date: Optional[date]
    last_modified: datetime

    episodic_memories: EpisodicAuditSection
    semantic_facts: SemanticAuditSection
    identity_memory: IdentityAuditSection
    personality_profile: PersonalityAuditSection
    longitudinal_data: LongitudinalAuditSection
    safety_record: SafetyAuditSection
    goals_and_threads: GoalAuditSection

class EpisodicAuditSection:
    count: int
    date_range: tuple[date, date]
    total_size_bytes: int
    memories: list[AuditableMemory]     # sorted by recency; paginated in UI

class AuditableMemory:
    memory_id: UUID
    date_formed: date
    human_readable_summary: str         # non-verbatim; 1–2 sentence description
    importance_label: Literal["Low", "Medium", "High", "Anchored"]
    topic_tags: list[str]
    emotion_at_formation: str           # e.g., "anxious", "happy", "neutral"
    reinforcement_count: int            # how many times referenced/strengthened
    has_been_used_in_response: bool     # has Nova referenced this in a conversation?
    derived_semantic_facts: list[UUID]  # semantic facts partially derived from this
    longitudinal_references: list[str] # e.g., "Referenced in Week of Jan 15 summary"
    # Actions available:
    # delete, downgrade_importance, decontextualize, anchor, expire, view_provenance

class SemanticAuditSection:
    count: int
    categories: SemanticFactCategories

class SemanticFactCategories:
    preferences: list[AuditableFact]        # communication prefs, style prefs
    relationships: list[AuditableFact]      # named people and relationship types
    life_context: list[AuditableFact]       # job, city, education, life phase
    habits: list[AuditableFact]             # recurring behavioral patterns
    goals_and_values: list[AuditableFact]   # stated goals, expressed values
    emotional_patterns: list[AuditableFact] # recurring emotional tendencies

class AuditableFact:
    fact_id: UUID
    fact_text: str                          # e.g., "You are a second-year CS student at a Bengaluru university"
    category: str
    confidence: float                       # displayed as "Low / Medium / High / Very High"
    first_inferred_date: date
    last_updated_date: date
    derived_from_episode_count: int         # how many sessions contributed to this
    source_episode_ids: list[UUID]          # backing episodic memories
    is_user_confirmed: bool                 # has user explicitly verified this?
    expiry_date: Optional[date]             # if user set an expiry
    # Actions: edit, delete, anchor, expire, view_provenance

class IdentityAuditSection:
    beliefs: list[AuditableBelief]
    values: list[AuditableBelief]
    defining_traits: list[AuditableBelief]

class AuditableBelief:
    belief_id: UUID
    belief_text: str                        # e.g., "You value intellectual honesty"
    centrality: float                       # displayed as "Peripheral / Moderate / Core / Foundational"
    formation_date: date
    last_reinforced_date: date
    evidence_count: int
    # Actions: edit, delete (with 24h undo window), anchor, request_clarification

class PersonalityAuditSection:
    traits: dict[str, TraitAuditEntry]      # keyed by trait name
    last_drift_date: date
    drift_magnitude_from_init: float        # displayed as "No drift / Minor / Moderate / Significant"
    drift_direction_summary: str            # e.g., "Nova has become slightly more formal with you"

class TraitAuditEntry:
    trait_name: str
    current_value: float                    # 0.0–1.0
    human_readable_description: str        # e.g., "warmth: high — Nova is quite warm with you"
    initial_value: float                    # population default at initialization
    delta_from_init: float

class LongitudinalAuditSection:
    chapter_count: int
    weekly_record_count: int
    oldest_record_date: Optional[date]
    current_chapter_title: str
    chapters: list[ChapterAuditEntry]
    # User can view, export, or delete individual chapters or summaries

class ChapterAuditEntry:
    chapter_id: UUID
    title: str
    date_range: tuple[date, Optional[date]]
    moment_count: int
    is_current: bool

class SafetyAuditSection:
    crisis_session_count: int               # count only; no content
    last_crisis_session_date: Optional[date] # date only; no content
    # Note: safety record content (tier, resources provided) is not shown here.
    # Only aggregate counts. User can request full safety record via separate process.

class GoalAuditSection:
    active_goal_count: int
    completed_goal_count: int
    abandoned_goal_count: int
    open_thread_count: int
    oldest_active_goal: Optional[str]       # goal title
```

### 5.3 Audit Query Interface

```python
class AuditQueryEngine:
    """
    Provides semantic query access to the live memory system.
    Returns actual memory objects with full metadata, not summaries.
    Uses the same retrieval pipeline as normal conversation.
    """

    def query(
        self,
        natural_language_query: str,
        memory_types: list[str] = None,     # filter by memory type if specified
        date_range: tuple[date, date] = None,
    ) -> AuditQueryResult:
        """
        Process a natural language audit query and return matching records.

        Examples:
        - "What do you know about my relationship with my family?"
        - "What memories do you have from last year?"
        - "What do you believe about my values?"
        - "What patterns have you noticed about me?"
        - "What do you know about my health?"
        - "What do you know about my career?"
        """

        # Parse query intent and extract key entities
        query_intent = classify_query_intent(natural_language_query)
        # query_intent.type: "relationship_query" | "temporal_query" | "topic_query" |
        #                     "identity_query" | "pattern_query" | "category_query"

        results = AuditQueryResult(query=natural_language_query, records=[])

        if query_intent.type == "temporal_query":
            # Date range extraction → episodic memory temporal filter
            extracted_range = query_intent.extracted_date_range or date_range
            results.records += memory_db.query_episodic_by_date_range(*extracted_range)
            results.records += longitudinal_store.query_summaries_by_date_range(*extracted_range)

        elif query_intent.type in ["topic_query", "relationship_query", "category_query"]:
            # Semantic search across episodic + semantic stores
            query_embedding = embed(natural_language_query)
            episodic_matches = vector_store.search(query_embedding, top_k=20)
            semantic_matches = semantic_store.search_by_topic(query_intent.extracted_topics)
            identity_matches = identity_store.search_by_topic(query_intent.extracted_topics)
            longitudinal_matches = longitudinal_store.search_by_topic(query_intent.extracted_topics)
            results.records += episodic_matches + semantic_matches + identity_matches + longitudinal_matches

        elif query_intent.type == "identity_query":
            results.records += identity_store.get_all()
            results.records += semantic_store.get_by_category("goals_and_values")

        elif query_intent.type == "pattern_query":
            results.records += semantic_store.get_by_category("emotional_patterns")
            results.records += semantic_store.get_by_category("habits")
            results.records += longitudinal_store.get_active_behavioral_patterns()

        # Filter by memory type if requested
        if memory_types:
            results.records = [r for r in results.records if r.memory_type in memory_types]

        # Sort by relevance + recency
        results.records = sort_by_relevance_and_recency(results.records, natural_language_query)
        results.total_count = len(results.records)

        return results
```

### 5.4 Provenance Trail

```python
class ProvenanceRecord:
    """
    For any memory in the audit, the user can view exactly where Nova got it.
    """
    memory_id: UUID
    memory_type: str

    # Source sessions
    primary_session_id: UUID
    primary_session_date: date
    source_moment_summary: str              # brief non-verbatim description of what was said
                                            # e.g., "You mentioned difficulty with a group project"

    # Reinforcement history
    reinforcement_events: list[ReinforcementEvent]
    total_reinforcement_count: int
    first_formed: date
    last_reinforced: date

    # Consolidation history (if semantic fact)
    was_consolidated_from_episodes: bool
    consolidation_episode_count: int        # how many episodes contributed
    consolidation_date: Optional[date]

    # Downstream derivations
    contributed_to_semantic_facts: list[tuple[UUID, str]]   # (fact_id, fact_text)
    contributed_to_personality_params: list[str]            # e.g., ["verbosity"]
    referenced_in_longitudinal: list[str]                   # human-readable references

class ReinforcementEvent:
    session_id: UUID
    date: date
    reinforcement_type: Literal["topic_recalled", "user_referenced", "nova_referenced", "consolidation"]
    strength_delta: float
```

### 5.5 Memory Correction Interface

```python
class MemoryCorrectionType(str, Enum):
    EDIT            = "edit"            # change content of a semantic fact
    DOWNGRADE       = "downgrade"       # reduce importance score
    DECONTEXTUALIZE = "decontextualize" # remove a topic tag
    ANCHOR          = "anchor"          # maximum persistence; never auto-expires
    EXPIRE          = "expire"          # set future auto-deletion date
    CONFIRM         = "confirm"         # user verifies this is accurate

class MemoryCorrectionRequest:
    memory_id: UUID
    correction_type: MemoryCorrectionType
    # For EDIT:
    new_content: Optional[str]
    # For DOWNGRADE:
    new_importance: Optional[Literal["Low", "Medium"]]
    # For DECONTEXTUALIZE:
    tags_to_remove: Optional[list[str]]
    # For EXPIRE:
    expiry_date: Optional[date]

def apply_correction(
    request: MemoryCorrectionRequest,
    memory_store: MemoryStore,
) -> CorrectionResult:
    """Apply a user correction to a memory object."""

    record = memory_store.get(request.memory_id)

    if request.correction_type == MemoryCorrectionType.EDIT:
        # Update content; recompute embedding from new content
        new_embedding = embed(request.new_content)
        memory_store.update(request.memory_id, {
            "content": request.new_content,
            "embedding": new_embedding,
            "is_user_confirmed": True,
            "last_corrected_at": datetime.utcnow(),
        })
        vector_store.update_embedding(request.memory_id, new_embedding)

    elif request.correction_type == MemoryCorrectionType.DOWNGRADE:
        new_score = {"Low": 0.20, "Medium": 0.50}[request.new_importance]
        memory_store.update(request.memory_id, {
            "importance_score": min(record.importance_score, new_score),
            "is_user_downgraded": True,
        })

    elif request.correction_type == MemoryCorrectionType.DECONTEXTUALIZE:
        updated_tags = [t for t in record.topic_tags if t not in request.tags_to_remove]
        memory_store.update(request.memory_id, {"topic_tags": updated_tags})

    elif request.correction_type == MemoryCorrectionType.ANCHOR:
        memory_store.update(request.memory_id, {
            "decay_rate": 0.0,      # no decay for anchored memories
            "importance_score": max(record.importance_score, 0.95),
            "is_anchored": True,
        })

    elif request.correction_type == MemoryCorrectionType.EXPIRE:
        memory_store.update(request.memory_id, {"auto_expiry_date": request.expiry_date})

    elif request.correction_type == MemoryCorrectionType.CONFIRM:
        memory_store.update(request.memory_id, {"is_user_confirmed": True})

    # Log correction event in audit.db
    audit_db.log_correction(request)
    return CorrectionResult(success=True, memory_id=request.memory_id)
```

---

## 6. Sub-Component 4 — Cross-Platform Sync

### 6.1 The Sync Tension

On-device memory is private because it never leaves the device. A companion that knows you needs to be available on all your devices. These goals conflict — and the resolution chosen here is: **the user holds the key.** Data travels through Nova's infrastructure as opaque ciphertext that the server cannot read, decrypted only by the user's devices using key material the server never holds.

### 6.2 Sync Delta Format

```python
class SyncDelta:
    """
    The atomic unit of synchronization.
    Not a full dump of the memory store — a compressed record of changes since last sync.
    Encrypted on-device before transmission. Server receives opaque bytes only.
    """
    delta_id: UUID
    user_id: str                            # used by server for routing only
    source_device_id: str                   # hashed; not personally identifying
    created_at: datetime
    sequence_number: int                    # monotonically increasing per device
    previous_delta_id: Optional[UUID]       # for chain integrity verification

    # Operations in this delta (stored as encrypted blob)
    operations: list[SyncOperation]         # encrypted; server cannot read

    # Encrypted payload (what the server actually sees)
    encrypted_payload: bytes                # AES-256-GCM(sync_backup_key, serialize(operations))
    payload_size_bytes: int                 # visible to server (routing only)
    payload_nonce: bytes                    # AES-GCM nonce; not sensitive

class SyncOperation:
    operation_type: Literal[
        "upsert_episodic",
        "upsert_semantic",
        "upsert_identity",
        "upsert_personality_vector",
        "upsert_longitudinal",
        "upsert_goal",
        "delete_memory",
        "apply_correction",
    ]
    record_id: UUID
    store_name: str                         # which database file
    serialized_record: bytes                # full serialized record
    timestamp: datetime
```

### 6.3 Sync Protocol — Full Sequence

```python
class SyncCoordinator:

    def push_delta(self, store_changes: list[SyncOperation]) -> SyncPushResult:
        """
        Package recent local changes into an encrypted delta and push to sync server.
        Called: whenever the device comes online after local changes were made.
        """
        # Step 1: Build the delta
        delta = SyncDelta(
            delta_id=uuid4(),
            user_id=self.user_id,
            source_device_id=hash_device_id(self.device_id),
            created_at=datetime.utcnow(),
            sequence_number=self._next_sequence_number(),
            previous_delta_id=self._last_pushed_delta_id(),
            operations=store_changes,
            encrypted_payload=b"",      # filled in next
            payload_size_bytes=0,
            payload_nonce=os.urandom(12),
        )

        # Step 2: Encrypt the operations payload
        plaintext = serialize(store_changes)
        sync_key = key_hierarchy.sync_backup_key
        ciphertext = aes_256_gcm_encrypt(sync_key, delta.payload_nonce, plaintext)
        delta.encrypted_payload = ciphertext
        delta.payload_size_bytes = len(ciphertext)

        # Step 3: Transmit to sync server
        # Server receives: delta_id, user_id, source_device_id (hashed),
        #                  sequence_number, payload_size_bytes, payload_nonce,
        #                  encrypted_payload
        # Server does NOT receive: operations plaintext, any key material
        response = sync_api.push_delta(delta)

        # Step 4: Update local sync state
        self._record_pushed_delta(delta.delta_id, delta.sequence_number)
        return SyncPushResult(success=response.ok, delta_id=delta.delta_id)

    def pull_and_apply(self) -> SyncPullResult:
        """
        Fetch deltas from other devices and apply them locally.
        Called: on app launch and every 15 minutes when online.
        """
        # Step 1: Fetch encrypted deltas from server
        last_known_seq = self._last_received_sequence_numbers_per_device()
        raw_deltas = sync_api.fetch_deltas_since(last_known_seq)

        applied_count = 0
        conflicts = []

        for raw_delta in raw_deltas:
            if raw_delta.source_device_id == hash_device_id(self.device_id):
                continue    # skip our own deltas echoed back

            # Step 2: Decrypt payload locally
            plaintext = aes_256_gcm_decrypt(
                key=key_hierarchy.sync_backup_key,
                nonce=raw_delta.payload_nonce,
                ciphertext=raw_delta.encrypted_payload,
            )
            operations = deserialize(plaintext)

            # Step 3: Apply each operation with conflict detection
            for op in operations:
                conflict = self._detect_conflict(op)
                if conflict:
                    conflicts.append(conflict)
                    resolved_op = self._resolve_conflict(op, conflict)
                    if resolved_op:
                        self._apply_operation(resolved_op)
                else:
                    self._apply_operation(op)
                    applied_count += 1

        return SyncPullResult(
            deltas_received=len(raw_deltas),
            operations_applied=applied_count,
            conflicts_detected=len(conflicts),
            conflicts=conflicts,
        )
```

### 6.4 Conflict Resolution — Full Specification

```python
class ConflictResolutionPolicy:
    """
    Per-memory-type conflict resolution when two devices modify the same record offline.
    """

    def resolve(self, op_from_remote: SyncOperation, local_record: Any) -> ResolvedOperation:

        store = op_from_remote.store_name

        # ── EPISODIC MEMORIES: No conflict possible ─────────────────────────
        if store == "episodic_memories":
            # A new episodic memory from device B doesn't exist on device A.
            # Simply insert it. Merge chronologically.
            return ResolvedOperation(action="insert", record=op_from_remote.serialized_record)

        # ── SEMANTIC FACTS: Last-write-wins with notification ────────────────
        elif store == "semantic_facts":
            remote_record = deserialize(op_from_remote.serialized_record)
            if local_record is None:
                return ResolvedOperation(action="insert", record=op_from_remote.serialized_record)
            if remote_record.last_updated_at > local_record.last_updated_at:
                self._queue_conflict_notification(
                    message=f"A fact was updated on another device: '{remote_record.fact_text}'. "
                            f"The most recent version has been kept.",
                    local_value=local_record.fact_text,
                    remote_value=remote_record.fact_text,
                )
                return ResolvedOperation(action="overwrite", record=op_from_remote.serialized_record)
            else:
                # Local is more recent — keep local; notify user
                self._queue_conflict_notification(...)
                return ResolvedOperation(action="keep_local")

        # ── IDENTITY MEMORY: Requires explicit user resolution ───────────────
        elif store == "identity_beliefs":
            remote_record = deserialize(op_from_remote.serialized_record)
            if local_record is None:
                return ResolvedOperation(action="insert", record=op_from_remote.serialized_record)
            if remote_record.content != local_record.content:
                # Surface both to user; block until resolved
                self._queue_identity_conflict_for_user_resolution(
                    record_id=op_from_remote.record_id,
                    local_version=local_record,
                    remote_version=remote_record,
                )
                return ResolvedOperation(action="hold_pending_user_resolution")
            return ResolvedOperation(action="keep_local")  # same content; no conflict

        # ── PERSONALITY VECTOR: Component-wise weighted merge ────────────────
        elif store == "personality_vector":
            remote_pv = deserialize(op_from_remote.serialized_record)
            local_pv = local_record

            merged_traits = {}
            for trait_name in local_pv.traits:
                local_val = local_pv.traits[trait_name]
                remote_val = remote_pv.traits.get(trait_name, local_val)
                # Weight by interaction count — more data → more weight
                local_weight = local_pv.interaction_count
                remote_weight = remote_pv.interaction_count
                total = local_weight + remote_weight
                merged_traits[trait_name] = (
                    (local_val * local_weight + remote_val * remote_weight) / total
                    if total > 0 else (local_val + remote_val) / 2
                )

            merged_pv = PersonalityVector(
                traits=merged_traits,
                interaction_count=local_pv.interaction_count + remote_pv.interaction_count,
                last_merged_at=datetime.utcnow(),
            )
            return ResolvedOperation(action="overwrite", record=serialize(merged_pv))

        # ── LONGITUDINAL DATA: Merge by timestamp; keep more complete ────────
        elif store in ["weekly_summaries", "life_chapters", "retrospective_packets"]:
            remote_record = deserialize(op_from_remote.serialized_record)
            if local_record is None:
                return ResolvedOperation(action="insert", record=op_from_remote.serialized_record)
            # If same period exists on both devices, keep the one with more content
            if len(remote_record.narrative_summary) > len(local_record.narrative_summary):
                self._queue_conflict_notification(
                    message="A longitudinal record was updated on another device. "
                            "The more complete version has been kept."
                )
                return ResolvedOperation(action="overwrite", record=op_from_remote.serialized_record)
            return ResolvedOperation(action="keep_local")

        # ── ALL OTHER: Last-write-wins ────────────────────────────────────────
        else:
            remote_record = deserialize(op_from_remote.serialized_record)
            if local_record is None or remote_record.updated_at > local_record.updated_at:
                return ResolvedOperation(action="overwrite", record=op_from_remote.serialized_record)
            return ResolvedOperation(action="keep_local")
```

### 6.5 Sync Configuration and Scope Control

```python
class SyncConfiguration:
    user_id: str
    sync_enabled: bool

    # Per-category sync toggles
    sync_episodic_memory: bool = True
    sync_semantic_memory: bool = True
    sync_identity_memory: bool = True
    sync_personality_vector: bool = True
    sync_longitudinal_data: bool = True
    sync_goal_state: bool = True
    sync_safety_record: bool = False        # most sensitive; off by default

    # Device-specific profile overrides
    device_profiles: list[DeviceSyncProfile]

class DeviceSyncProfile:
    device_id_hash: str                     # hashed device identifier
    profile_name: str                       # e.g., "Work Laptop", "Personal Phone"
    override_toggles: dict[str, bool]       # overrides specific to this device
    # Example: on work laptop, sync only semantic + personality + goals
    # { "sync_episodic_memory": False,
    #   "sync_identity_memory": False,
    #   "sync_longitudinal_data": False,
    #   "sync_safety_record": False }
```

### 6.6 Sync Server Trust Model

```python
SYNC_SERVER_TRUST_MODEL = {
    "what_server_knows": [
        "User account identifier (for routing to correct blob store)",
        "Encrypted blob sizes and timestamps (for storage management and sync ordering)",
        "Whether a sync event occurred and when (usage analytics, opt-in only)",
    ],
    "what_server_never_knows": [
        "Any plaintext content of any memory",
        "User name, location, conversation history, or any personal data",
        "The encryption key — it never travels to or through the server",
        "What data is inside the encrypted blobs",
        "The semantic meaning of any stored data",
    ],
    "attack_resistance": {
        "rogue_employee_with_full_server_access": "Cannot access any user memory content",
        "government_legal_order": "Cannot produce plaintext user data — server does not have it",
        "server_data_breach": "Attacker receives only opaque ciphertext — useless without key",
        "only_viable_attack_vector": "User's own device — physical access + passphrase required",
    },
    "key_material_flow": {
        "sync_backup_key": "Generated on device → never transmitted → rederived from passphrase on new device",
        "sync_salt": "Stored on server (not sensitive — it's just random bytes) → used to rederive key",
        "server_role": "Opaque blob relay only — routing identifier + encrypted payload",
    },
}
```

---

## 7. Privacy Agent — Coordination Architecture

```python
class PrivacyAgent:
    """
    Persistent background service running on the user's device.
    Coordinates all four Layer 12 sub-components.
    Runs independently of the conversation pipeline.
    """

    components: {
        "encryption_manager":   EncryptionManager,     # key lifecycle, rotation, validation
        "deletion_executor":    DeletionExecutor,       # deletion requests + cascade handling
        "audit_index_builder":  AuditIndexBuilder,      # maintains audit.db index for fast retrieval
        "sync_coordinator":     SyncCoordinator,        # delta computation + conflict resolution
        "integrity_verifier":   IntegrityVerifier,      # daily Merkle hash verification
        "consent_manager":      ConsentManager,         # user privacy preferences + DPDP compliance
    }

    schedule: {
        "integrity_check":          "daily at 3am local time",
        "audit_index_refresh":      "on every memory write (incremental update)",
        "sync_check":               "every 15 minutes when online",
        "key_rotation":             "every 90 days (prompted, not forced)",
        "expiry_check":             "daily — delete memories that have passed their expiry_date",
        "deletion_certificate_archive": "immediately on deletion completion",
    }


class AuditIndexBuilder:
    """
    Maintains audit.db as a pre-computed index over all memory stores.
    This makes Memory Audit queries fast without re-scanning live stores every time.
    """

    def rebuild_full_index(self) -> None:
        """Full rebuild — called weekly or after major operations."""
        audit_db.clear_audit_index()
        for store_name in STORE_ARCHITECTURE:
            records = read_all_records(store_name)
            for record in records:
                audit_db.insert_audit_index_entry(
                    record_id=record.id,
                    store_name=store_name,
                    topic_tags=record.topic_tags,
                    date=record.created_at,
                    human_summary=generate_human_readable_summary(record),
                    importance_label=map_importance_to_label(record.importance_score),
                )

    def incremental_update(self, operation: str, record: Any) -> None:
        """Called on every write to memory stores. Keeps index current."""
        if operation == "insert":
            audit_db.insert_audit_index_entry(...)
        elif operation == "update":
            audit_db.update_audit_index_entry(record.id, ...)
        elif operation == "delete":
            audit_db.remove_audit_index_entry(record.id)


class ConsentManager:
    """
    Tracks and enforces user privacy preferences.
    Each preference is a separate consent record with timestamp and provenance.
    Required for DPDP Act compliance (Section 6 — valid consent).
    """

    def record_consent(
        self,
        consent_type: str,
        granted: bool,
        user_initiated: bool,
        timestamp: datetime,
    ) -> ConsentRecord:
        record = ConsentRecord(
            consent_id=uuid4(),
            user_id=self.user_id,
            consent_type=consent_type,
            granted=granted,
            granted_at=timestamp if granted else None,
            revoked_at=timestamp if not granted else None,
            user_initiated=user_initiated,
            version=self._current_privacy_policy_version(),
        )
        audit_db.insert_consent_record(record)
        return record

    def is_consent_active(self, consent_type: str) -> bool:
        latest = audit_db.get_latest_consent(self.user_id, consent_type)
        return latest is not None and latest.granted

CONSENT_TYPES = [
    "cloud_backup_sync",                # optional; off by default
    "usage_telemetry",                  # anonymized, opt-in
    "weekly_summary_delivery",          # Layer 10 delivery; off by default
    "proactive_checkins",               # Layer 6; on by default but revocable
    "crisis_session_logging",           # Layer 11 safety record; non-revocable
    "memory_for_personalization",       # core feature; revoking disables memory
]
```

---

## 8. DPDP Act Compliance Map

NovaAI is being built in India. The **Digital Personal Data Protection Act, 2023 (DPDP Act)** is the primary regulatory framework. Layer 12's architecture is designed with explicit DPDP compliance built in, not bolted on.

| DPDP Act Right | Relevant Section | Layer 12 Implementation |
|---|---|---|
| Right to access personal data | Section 11 | Memory Audit Memory Map + query interface — all personal data, in legible form, accessible at any time |
| Right to correction | Section 12 | Memory Audit correction interface — edit, anchor, decontextualize |
| Right to erasure | Section 12 | Selective Deletion — all 6 deletion types with deletion certificate as proof |
| Right to grievance redressal | Section 13 | Deletion certificates + provenance trails + sync audit logs provide evidentiary basis |
| Data minimization | Section 6 (purpose limitation) | Memory decay engine, consolidation compression, expiry mechanism — only what is necessary is retained |
| Valid consent | Section 6 | ConsentManager records each consent separately with timestamp, version, and revocability |
| Data fiduciary obligations | Section 8 | On-device storage, zero-knowledge sync, no server-side content access |

---

## 9. Error Handling and Degraded-Mode Behavior

| Failure Case | Fallback |
|---|---|
| Key derivation fails (wrong passphrase) | Return auth error; do not attempt to read stores; do not expose partial data |
| Key rotation fails mid-operation | Abort rotation; rollback to old key; log error; retry in 24 hours |
| Sync push fails (network unavailable) | Queue delta locally; retry with exponential backoff; max 72-hour queue before notifying user |
| Sync pull conflict cannot be auto-resolved (identity memory) | Hold in conflict queue; notify user at next session open; do not apply either version until resolved |
| Deletion cascade computation times out | Abort deletion; present partial cascade report to user; user decides whether to proceed with partial information |
| Integrity check detects mismatch | Alert user immediately; do not silence; provide option to restore from backup or export current state |
| Audit index rebuild fails | Fall back to live store queries (slower); rebuild retry scheduled for next night |
| `audit.db` corruption detected | Rebuild from live stores; log event; notify user |
| Memory store file unreadable (corruption) | Present user with recovery options: restore from encrypted backup, or export what is recoverable |
| `memory.vdb` vector store corruption | Rebuild embeddings from stored text content in `memory.db`; log event; no data loss if `memory.db` intact |

---

## 10. Performance Targets

| Operation | Target | Notes |
|---|---|---|
| Memory read (single record, by ID) | < 5ms | SQLite direct lookup; encrypted at rest |
| Vector similarity search (top-10, 50k vectors) | < 20ms | hnswlib in-process; no network |
| Audit index query (natural language) | < 150ms | Audit index lookup + embedding search |
| Deletion dry run (cascade computation) | < 2 seconds | Local computation; no LLM call |
| Deletion execution (single memory) | < 500ms | Includes secure zero, vector removal, cascade |
| Deletion execution (topic-based, ~50 memories) | < 10 seconds | Larger cascade; user shown progress |
| Sync delta push (incremental, ~10 operations) | < 3 seconds | Network-dependent; encrypted before transmission |
| Sync pull and apply (single device's deltas) | < 5 seconds | Network-dependent; decrypt and apply |
| Integrity check (full Merkle recompute) | < 60 seconds | Runs at 3am; no user latency impact |
| Key rotation (re-encrypt all stores) | < 5 minutes | Background; notifies user when complete |
| Audit index full rebuild | < 30 seconds | Weekly; no user latency impact |

---

## 11. Data Export — User Portability

```python
class DataExportRequest:
    """
    The user can request a full export of all their data at any time.
    This is their data — they have an unconditional right to take it with them.
    """
    user_id: str
    export_format: Literal["json", "markdown", "pdf"]
    include: ExportScope

class ExportScope:
    include_episodic_memories: bool = True
    include_semantic_facts: bool = True
    include_identity_memory: bool = True
    include_personality_profile: bool = True
    include_longitudinal_data: bool = True  # narrative arc, weekly summaries
    include_goal_history: bool = True
    include_safety_record: bool = False     # excluded by default; opt-in

def generate_export(request: DataExportRequest) -> ExportPackage:
    """
    Generate a human-readable export of all requested data.
    Does NOT include raw database files or key material.
    Produces a structured document the user can read and keep.
    """
    sections = []

    if request.include.include_episodic_memories:
        sections.append(export_episodic_memories_as_readable_log())

    if request.include.include_semantic_facts:
        sections.append(export_semantic_facts_as_fact_sheet())

    if request.include.include_longitudinal_data:
        sections.append(export_narrative_arc_as_story())

    if request.include.include_goal_history:
        sections.append(export_goal_history_as_timeline())

    export_document = assemble_export_document(sections, format=request.export_format)

    return ExportPackage(
        document=export_document,
        generated_at=datetime.utcnow(),
        format=request.export_format,
        size_bytes=len(export_document),
    )
```

---

## 12. Design Principles

1. **The user's data is their data, not Nova's.** Every piece of information in every store was given to Nova by the user, inferred from what the user shared, or derived from the user's behavior. Nova is the custodian, not the owner. The user has unconditional rights to access, correct, export, and delete it — and Layer 12 makes exercising those rights easy and complete.

2. **Privacy must be verifiable, not just claimed.** The Memory Audit, the deletion certificate, the Merkle integrity check, and the provenance trail collectively make "Nova only knows what you've told it" a statement you can verify. This is categorically different from a privacy policy that says the same thing.

3. **Zero-knowledge sync is the correct architecture for this data.** Any sync architecture where Nova's servers hold keys — even briefly, even just for routing — is incompatible with the privacy guarantee. The only viable architecture is one where the server is a dumb relay: it stores encrypted blobs it cannot read, routes them to the correct devices, and knows nothing about their content.

4. **Selective deletion must be genuinely surgical.** Telling a user they can delete a memory while silently retaining semantic facts derived from it, longitudinal references to it, or personality parameters shaped by it is a deceptive implementation of deletion. Layer 12 surfaces the full cascade before execution and completes it fully.

5. **Trust is built through transparency, not through assurance.** Users who understand exactly what Nova knows — and know they can change or delete any of it — will share more deeply and use Nova more fully than users who have to take the privacy promise on faith. Layer 12 is not in tension with Nova's capability as a companion. It is what makes that capability possible.

---

## 13. Live Wiring Status (current state)

**Module map:** SC-1 `encryption_manager.py` (key hierarchy + authenticated encryption) +
`integrity_verifier.py` (Merkle tamper detection, §3.4); SC-2 `selective_deletion.py` (§4); SC-3
`memory_audit.py` (transparency view + query + provenance, §5) + `correction_interface.py` (the
six corrections, §5.5); SC-4 `sync_coordinator.py` (zero-knowledge deltas + conflict resolution,
§6); `privacy_agent.py` (coordinator: consent, deletion lifecycle, audit, integrity, §7);
`schemas.py`. All stores (memory/semantic/identity/personality/longitudinal/safety/goal), the
embedder, and the certificate signer are injected, so the layer runs and is tested fully offline
with no database, network, or sync server. 62 unit tests: `test_encryption_manager` (9),
`test_integrity_verifier` (7), `test_selective_deletion` (11), `test_memory_audit_view` (9),
`test_correction_interface` (8), `test_sync_coordinator` (10), `test_privacy_agent` (8).

- **SC-1 On-Device Memory (encryption)** — algorithms implemented and tested, **not deployed**;
  this is a genuine undeployed infra project, not a wiring gap. The spec mandates AES-256-GCM /
  SQLCipher / Argon2id with keys in the Secure Enclave; the test runtime is stdlib-only, so
  `encryption_manager` implements a *real* authenticated-encryption construction from stdlib
  primitives instead — PBKDF2-HMAC-SHA256 (master key), RFC-5869 HKDF (derived key hierarchy), a
  SHA-256 counter-mode keystream, and HMAC-SHA256 encrypt-then-MAC with constant-time
  verification. It genuinely round-trips, detects tampering, and rejects wrong keys. Production
  would swap the cipher for AES-256-GCM behind the same key hierarchy and use Argon2id for the
  sync key (PBKDF2 iterations default to 600k here; tests pass a lower value for speed). No code
  outside tests instantiates `EncryptionManager` or `IntegrityVerifier` today — memory-at-rest in
  this codebase is plain Postgres/SQLite, and the SQLCipher/Secure-Enclave design remains a
  deployment project.
- **SC-2 Selective Deletion** — fully live, the one sub-component with a real production caller
  end to end. `api/routes/privacy.py`'s `DELETE /memory/{memory_id}` builds a
  `_EpisodicDeletionStore` duck-type adapter over `PostgresMemoryStore` and calls
  `create_deletion_request` → `dry_run_deletion` → `execute_deletion` for real, single-memory
  deletions — verified end-to-end (`tests/unit/api/test_routes_privacy.py`): the deleted memory
  404s on `GET`, disappears from `GET /memory/audit`, and is unrecallable through the
  `GET /memory/search` keyword-scan fallback, not just logically flagged. Two adapter-layer bugs
  were found and fixed while wiring this in (both in `selective_deletion.py`, no behavior change
  to the live caller's observable output since `PostgresMemoryStore.delete_episodic` already
  independently zeroed `summary`/`embedding` regardless): `execute_deletion` read
  `getattr(record, "content", ...)`, a field that doesn't exist on `EpisodicMemory` (the real
  field is `summary`), making the "secure zero before delete" step a silent no-op — fixed to zero
  whichever of `content`/`summary` the record actually has, using `""` rather than the original
  `"\x00" * len(content)` NUL-padding (Postgres `jsonb` rejects NUL bytes, and `EpisodicMemory`
  payloads are JSONB, so the original code would have raised had it ever actually run against
  real content); and `dry_run_deletion`'s `summary_human_readable` always opened with
  `"...will also:"` even when no cascade stores were wired, misleadingly reading as "nothing else
  affected" rather than "nothing else was checked" — fixed to state plainly whether cascade impact
  was computed at all. **Cascade reporting is now real** (not just the primary-store delete):
  `api/routes/privacy.py` wires `_SemanticDeletionStore` and `_LongitudinalDeletionStore` adapters
  (same duck-type pattern as `_EpisodicDeletionStore`) into `dry_run_deletion`, after fixing two
  field-mismatch bugs found in the process — the semantic cascade loop read
  `fact.derived_from_episodes`/`fact.fact_id`/`fact.fact_text` (real fields:
  `supporting_episode_ids`/`memory_id`/`statement`), and the longitudinal cascade loop read
  `s.backing_episode_ids` on `WeeklySummary` (that field only exists on `RetrospectivePacket`; the
  real per-summary anchor is `most_emotionally_significant_moment.episode_ids`) — plus a type
  mismatch where `resolve_scope`'s `target` set holds plain strings but
  `SemanticMemory.supporting_episode_ids` deserializes to `UUID` objects, so `e in target` would
  silently never match even with field names fixed (`UUID(...) == "some-string"` is `False` in
  Python); both loops now compare on `str(...)` form. Proven by
  `tests/unit/api/test_routes_privacy.py::test_delete_memory_reports_a_real_semantic_cascade`.
  **Cascade mutation is also real**, not just reporting: product decision (2026-08-09) was redact
  in place rather than hard-delete — `selective_deletion.redact_cascade` strips the deleted
  episode's id from every affected semantic fact's `supporting_episode_ids` (a fact left with zero
  remaining support is deprecated and its `statement` cleared, the same "logical deletion, row
  retained for proof" invariant the memory-deletion path itself uses), and a weekly summary whose
  `most_emotionally_significant_moment` pointed only at the deleted episode has that field
  cleared; wired into `DELETE /memory/{id}` right after `execute_deletion`. Personality-vector
  cascade (`personality_store.simulate_removal_impact`) stays permanently unreported — no real
  "personality vector" store exists anywhere in this codebase to check against; the parameter is
  accepted and skipped, not stubbed.
- **SC-3 Memory Audit + Correction** — live. `GET /memory/audit/full`, `GET /memory/audit/query`,
  and `POST /memory/{id}/correct` wire `memory_audit.generate_audit_view`/`query` and
  `correction_interface.apply_correction` for real (`api/routes/privacy.py`); the older flat
  `GET /memory/audit` route remains a separate, simpler episodic/semantic list built directly in
  the route rather than Layer 12's richer 7-section view. Wiring the real routes surfaced the same
  class of field-mismatch bug as SC-2's cascade work: `_to_auditable_fact` read
  `f.fact_id`/`fact_text`/`category`/`source_episode_ids`, none of which exist on the real
  `SemanticMemory` (`memory_id`/`statement`/`memory_type`/`supporting_episode_ids`) — fixed.
  `IdentityMemory` (`belief_id`/`category`/no `confidence`) is a different real shape again, so it
  gets its own converter, `_to_auditable_identity`, rather than one function duck-typing two
  incompatible schemas. The correction interface had the mirror problem: five of its six
  correction types wrote field names (`content`/`is_anchored`/`is_user_downgraded`/
  `auto_expiry_date`/`is_user_confirmed`/`last_corrected_at`) that don't exist on `EpisodicMemory`,
  silently no-op'd by `update_episodic`'s `hasattr` guard — `EpisodicMemory` gained those five
  fields (additive, default `False`/`None`, safe for the existing JSONB payload), and `EDIT` now
  writes both `content` and `summary`. Persisting the field alone left EXPIRE incomplete: nothing
  consumed `auto_expiry_date` until Layer 2's `decay_sweep` was updated to check it
  unconditionally, ahead of the strength-based decision (`ANCHOR`'s `decay_rate=0.0` verified to
  still survive the sweep untouched; both have regression tests in
  `tests/unit/test_forgetting_engine.py`). All six correction types are now genuinely functional
  end to end. Note: `tests/unit/test_memory_audit.py` belongs to **Layer 2** (the audit trail);
  Layer 12's own audit tests live in `test_memory_audit_view.py`.
- **SC-4 Cross-Platform Sync** — live, correctly split across client/server rather than merged.
  `sync_coordinator.py` (`build_delta`/`decrypt_delta`/`resolve_conflict`) is genuinely
  **client-side** code: it requires a `sync_key` only a device holds, and the zero-knowledge
  property depends on the server never seeing that key, let alone decrypting or resolving
  conflicts on plaintext. `api/routes/sync.py` correctly never imports it — `PostgresSyncStore` is
  the only thing the **server** (all this backend-only repo contains) could ever call; importing
  `SyncCoordinator` server-side would break the zero-knowledge guarantee it exists to provide. An
  earlier audit pass framed this as two divergent implementations that had "diverged" and implied
  a reconciliation was owed; on closer read they were never competing — `SyncCoordinator` has no
  server caller by design, not by neglect, and stays exactly where a future on-device client would
  import it from. Worth remembering as a category: not every apparent "duplicate implementation"
  is a duplication — check whether it's actually a correct client/server split before merging.
- **`privacy_agent.py`** (the SC-1–4 coordinator, consent management via `ConsentManager`) — has
  no caller anywhere, and this is a deliberate scope decision, not a gap: single-user local
  deployment has no real operation that needs to be gated behind consent today. Left as the
  in-memory-only, unwired module it already was.
- **`/memory/integrity`** verifies **`PostgresAuditTrail`** (Layer 2's SHA-256 hash chain) and
  **`PostgresPrivacyAudit`** (`infra/db/privacy_audit.py`, a separate SHA-256 chain logging
  deletion events) — both real, both live. Neither is Layer 12's own `integrity_verifier.py` (a
  Merkle-tree design over on-device store files); that module has no caller, consistent with SC-1
  remaining undeployed.
- **Design deviations from the original May-28 scaffold (reconciled, not a gap):** the scaffold's
  older `forget_*` deletion names were replaced by the authoritative six-type taxonomy. The full
  SQLCipher STORE_ARCHITECTURE, Secure-Enclave key storage, and on-disk DB files remain deployment
  concerns beyond the unit layer; the algorithms (key derivation, integrity, deletion, sync,
  audit) are implemented and tested here.

See `docs/POLISH_BACKLOG.md` for remaining larger structural items (deploy real
encryption-at-rest; decide whether any UI needs it beyond the now-live routes).

## 14. Decision Log

- **2026-08-04 (Phase 12 polish pass):** Audited `backend/layer12_privacy/` — found only SC-2
  (Selective Deletion) had a production caller; SC-1, SC-3, SC-4, and `privacy_agent.py` were
  complete and unit-tested but had zero callers. Fixed two `selective_deletion.py` bugs found
  while examining the one live caller (wrong field name silently no-op'ing secure-zero; a
  misleading "will also:" cascade message when no cascade stores were wired). Flagged SC-4's
  apparent client/server "divergence" as needing reconciliation — later corrected (see below).
- **2026-08-09 (follow-up):** Corrected the SC-4 framing — the client (`SyncCoordinator`) and
  server (`PostgresSyncStore`) split is a deliberate zero-knowledge-preserving architecture, not a
  divergent duplication needing reconciliation. No code changed; this was a documentation error in
  `docs/POLISH_BACKLOG.md`/`CLAUDE.md` corrected at the source.
- **2026-08-09 (follow-up):** Wired real semantic/longitudinal cascade stores into
  `dry_run_deletion`'s reporting via two new adapters, finding and fixing two field-mismatch bugs
  (`SemanticMemory`, `WeeklySummary`) and one string/UUID comparison bug that would have made the
  fixed field names silently still not match. Scoped explicitly to *reporting* only —
  `execute_deletion` still mutates only the primary episodic store at this point.
- **2026-08-09 (follow-up, product decisions confirmed with the user):** Wired `GET
  /memory/audit/full`, `GET /memory/audit/query`, and `POST /memory/{id}/correct` live for the
  first time, fixing the same class of field-mismatch bugs found in the prior entry (this time in
  `memory_audit.py`'s auditable-fact/-identity converters and `correction_interface.py`'s five
  broken correction types) plus adding five missing fields to `EpisodicMemory` and teaching
  `decay_sweep` to honor `auto_expiry_date`. Made cascade *mutation* real (redact-in-place, not
  hard-delete) via `selective_deletion.redact_cascade`. Decided to leave `ConsentManager` unwired
  — no real single-user operation needs consent-gating today.
- **2026-08-12:** Polish pass. Split `schemas.py` (251L) into a `schemas/` package and
  `selective_deletion.py` (251L) into `deletion_scope.py` + `deletion_cascade.py` +
  `selective_deletion.py` (now certificate + execution only), all re-exported. Wired
  `DeletionScope.date_range` into `resolve_scope`'s TOPIC_BASED branch (confirmed with the user —
  cheap, completes an already-half-built filter). Deleted
  `CascadeImpactReport.chapters_affected`/`.chapter_merge_required` (would need a 4th cascade
  store type never added as a `dry_run_deletion` param) and 4 doc-only `DeletionScope` fields
  never implemented in code at all (`semantic_category`, `identity_category`,
  `weekly_summary_ids`, `retrospective_ids`). Logged, not fixed: `execute_deletion` only ever
  mutates `memory_store` regardless of `deletion_type` — correct today only because the one live
  caller always issues SINGLE_MEMORY requests; a real caller for the other four types would need
  multi-store dispatch, a design gap not a routine fix.

---

*This document specifies Layer 12 completely. All four sub-components — SC-1 On-Device Memory (hybrid storage tiering table, complete KeyHierarchy schema with all four key types and derivation algorithms, KeyLifecycleManager with rotation and destruction operations, full STORE_ARCHITECTURE map with 8 database files, IntegrityVerifier with Merkle tree algorithm and tamper detection), SC-2 Selective Deletion (6 DeletionType values with undo windows and confirmation requirements, DeletionRequest and DeletionScope schemas, CascadeImpactReport schema, dry run algorithm computing cascade across semantic facts, personality vector, and longitudinal references, DeletionExecutor with secure zero overwrite and deletion certificate generation), SC-3 Memory Audit (MemoryAuditView with all 7 sections and complete AuditableMemory/AuditableFact/AuditableBelief/PersonalityAuditSection schemas, AuditQueryEngine with 5 query intent types and retrieval logic, ProvenanceRecord with reinforcement event log, full MemoryCorrectionRequest with all 6 correction types and apply logic), SC-4 Cross-Platform Sync (SyncDelta and SyncOperation schemas, push_delta and pull_and_apply protocol, ConflictResolutionPolicy with per-memory-type resolution for all 5 memory types, SyncConfiguration and DeviceSyncProfile schemas, sync server trust model) — are fully specified. The Privacy Agent coordination architecture, AuditIndexBuilder, ConsentManager with all 6 consent types, DPDP Act compliance map, error handling for all 10 failure cases, performance targets, data export mechanism, and design principles are all explicitly defined. No behavior of Layer 12 requires assumptions or inferences from other documents.*
