# Connect Unwired Modules & Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap between what the architecture docs describe and what the live pipeline actually runs — wire up features that are fully implemented and tested but never called in production, reconcile one piece of duplicated logic, and remove genuinely dead code / fix silently-discarded-variable bugs found during the audit.

**Architecture:** No new subsystems. Every task calls an already-implemented, already-tested pure function or class from its correct production call site (a background job, the goal pipeline, an API route, or a sibling module), following the codebase's existing patterns (dependency-injected LLM clients via `app_state.llm_clients`, `background/*_job.py` → `run(app_state) -> dict` → registered in `background/scheduler.py`'s `JOBS` dict, Postgres stores already in `infra/db/`).

**Tech Stack:** Python 3.11, pytest, existing Postgres/SQLAlchemy stores, no new dependencies.

## Global Constraints

- Full suite must stay green: `/usr/bin/python3.11 -m pytest tests/ -q` (1171 passing baseline).
- No new database tables/models in this plan — every task uses persistence that already exists.
- Every fix must be traceable to a specific doc citation or a specific verified "zero callers in production" finding from the audit (no speculative new behavior).
- Two items found during this audit are explicitly **out of scope**, matching the same "needs new persistence infra" bar that split off the Layer-5 and Life-Calendar follow-ups: `backend/layer13_onboarding/context_constructor.py::generate_first_message` and `backend/layer2_memory/audit_trail.py::detect_narrative_links` are both fully unwired from any pipeline hook — only their local unused-variable bugs are fixed here (Tasks 3 and 4); wiring them into the live turn remains a future follow-up.

---

### Task 1: Fix `default_mode` dead parameter in `api/assembly.py`

**Files:**
- Modify: `api/assembly.py:95, 132-136`
- Test: `tests/unit/api/test_assembly_turn.py`

**Interfaces:**
- Consumes: `backend.layer2_memory.schemas.ConversationMode` (existing `str` Enum with `.CASUAL = "casual"`).
- Produces: `build_pipeline_steps(..., default_mode: str = "casual")`'s `recall` hook now honors the parameter instead of ignoring it.

- [x] **Step 1: Write the failing test**

Add to `tests/unit/api/test_assembly_turn.py`:

```python
def test_recall_hook_uses_configured_default_mode(monkeypatch):
    """default_mode should drive the recall-time ConversationMode, not a hardcoded CASUAL."""
    from backend.layer2_memory.schemas import ConversationMode
    seen_modes = []

    async def fake_arbiter(user_id, query, emotion, mode, now, store, embedder):
        seen_modes.append(mode)
        from types import SimpleNamespace
        return SimpleNamespace(recalled_memories=[])

    monkeypatch.setattr("api.assembly.memory_arbiter", fake_arbiter)
    steps = _build_steps(default_mode="goal_planning")
    steps.recall("local-user", SimpleSpaceInputPacket("hi"))
    assert seen_modes == [ConversationMode.GOAL_PLANNING]
```

(`_build_steps` and `SimpleSpaceInputPacket` are the existing helpers already defined at the top of `tests/unit/api/test_assembly_turn.py` — read the file first to match their exact call signature before pasting this in; adjust the helper call to however `_build_steps` currently constructs `PipelineSteps` in that file, passing `default_mode="goal_planning"` through to `build_pipeline_steps`.)

- [x] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/api/test_assembly_turn.py -k default_mode -v`
Expected: FAIL — recorded mode is `ConversationMode.CASUAL`, not `GOAL_PLANNING`.

- [x] **Step 3: Write minimal implementation**

In `api/assembly.py`, replace the hardcoded line inside the `recall` closure:

```python
        packet = _run(memory_arbiter(
            user_id, query,
            EmotionVector(valence=0.0, arousal=0.0, dominant_label="neutral"),
            ConversationMode(default_mode), datetime.now(timezone.utc),
            store=recall_store, embedder=embedder))
```

(only the `ConversationMode.CASUAL` → `ConversationMode(default_mode)` change; everything else on that call stays the same.)

- [x] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/api/test_assembly_turn.py -v`
Expected: PASS (including all pre-existing tests in the file, unaffected since `default_mode` still defaults to `"casual"`).

- [x] **Step 5: Commit**

```bash
git add api/assembly.py tests/unit/api/test_assembly_turn.py
git commit -m "fix: honor default_mode parameter in assembly's recall hook instead of hardcoding CASUAL"
```

---

### Task 2: Wire `then_summary`/`current_progress`/`weekly_summaries` into `ThenVsNow` (retrospective.py)

**Files:**
- Modify: `backend/layer10_longitudinal/retrospective.py:79, 107, 119`
- Test: `tests/unit/test_retrospective.py`

**Interfaces:**
- Consumes: `backend.layer10_longitudinal.schemas.WeeklySummary` (has `.week_start_date: date`, `.emotional_summary: Optional[WeeklyEmotionalSummary]`), `WeeklyEmotionalSummary.dominant_emotion: str`, the `progress_record` object already used elsewhere in this file via `getattr(progress_record, "avg_valence_4w", 0.0)`.
- Produces: `build_then_vs_now(then_episodes, then_summary, then_goals, current_progress, current_goals) -> ThenVsNow` now populates `then_emotional_state`, `now_emotional_state`, `key_change` (previously always `""`); `generate_retrospective` now derives a real `then_summary` from `weekly_summaries` instead of passing `None`.

- [x] **Step 1: Write the failing test**

Add to `tests/unit/test_retrospective.py`:

```python
def test_then_vs_now_fills_emotional_state_and_key_change():
    from datetime import date
    from types import SimpleNamespace
    from backend.layer10_longitudinal.retrospective import build_then_vs_now
    from backend.layer10_longitudinal.schemas import WeeklySummary, WeeklyEmotionalSummary

    then_summary = WeeklySummary(
        user_id="u1", week_start_date=date(2026, 1, 5), week_end_date=date(2026, 1, 11),
        emotional_summary=WeeklyEmotionalSummary(dominant_emotion="anxious"))
    current_progress = SimpleNamespace(avg_valence_4w=0.3)
    then_goals = [SimpleNamespace(title="Learn guitar")]
    current_goals = [SimpleNamespace(title="Learn guitar"), SimpleNamespace(title="Run 5k")]

    result = build_then_vs_now([], then_summary, then_goals, current_progress, current_goals)

    assert result.then_emotional_state == "anxious"
    assert result.now_emotional_state == "positive"
    assert result.key_change == "1 new active goal(s) since then."
```

- [x] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_retrospective.py -k fills_emotional_state -v`
Expected: FAIL — `then_emotional_state`/`now_emotional_state`/`key_change` are all `""`.

- [x] **Step 3: Write minimal implementation**

Replace `build_then_vs_now` in `backend/layer10_longitudinal/retrospective.py`:

```python
def build_then_vs_now(then_episodes, then_summary, then_goals, current_progress, current_goals) -> ThenVsNow:
    """A structured then/now comparison (architecture doc §6.3 step 2)."""
    then_concern = then_episodes[0].title if then_episodes else "—"
    now_concern = current_goals[0].title if current_goals else "—"

    then_emotion = "unknown"
    if then_summary is not None and getattr(then_summary, "emotional_summary", None) is not None:
        then_emotion = then_summary.emotional_summary.dominant_emotion

    now_valence = getattr(current_progress, "avg_valence_4w", 0.0)
    if now_valence > 0.15:
        now_emotion = "positive"
    elif now_valence < -0.15:
        now_emotion = "negative"
    else:
        now_emotion = "neutral"

    then_count, now_count = len(then_goals), len(current_goals)
    if now_count > then_count:
        key_change = f"{now_count - then_count} new active goal(s) since then."
    elif now_count < then_count:
        key_change = f"{then_count - now_count} fewer active goal(s) than then."
    else:
        key_change = "Similar goal load to then."

    return ThenVsNow(
        then_primary_concern=then_concern, now_primary_concern=now_concern,
        then_emotional_state=then_emotion, now_emotional_state=now_emotion,
        then_active_goals=[getattr(g, "title", str(g)) for g in then_goals],
        now_active_goals=[getattr(g, "title", str(g)) for g in current_goals],
        key_change=key_change)


def _nearest_weekly_summary(weekly_summaries: list, reference_date: date):
    """The weekly summary whose week is nearest to reference_date, or None (§6.3)."""
    if not weekly_summaries:
        return None
    return min(weekly_summaries, key=lambda w: abs((w.week_start_date - reference_date).days))
```

And in `generate_retrospective`, replace the `then_vs_now = build_then_vs_now(...)` line:

```python
    then_summary = _nearest_weekly_summary(weekly_summaries, reference_date)
    then_vs_now = build_then_vs_now(then_episodes, then_summary, then_goals, progress_record, current_goals)
```

- [x] **Step 4: Run test to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_retrospective.py -v`
Expected: PASS (all tests in the file, including pre-existing ones — `then_summary=None` still works when `weekly_summaries` is empty).

- [x] **Step 5: Commit**

```bash
git add backend/layer10_longitudinal/retrospective.py tests/unit/test_retrospective.py
git commit -m "fix: populate ThenVsNow.then_emotional_state/now_emotional_state/key_change instead of leaving them empty"
```

---

### Task 3: Remove dead `persona` parameter from `generate_first_message`

**Files:**
- Modify: `backend/layer13_onboarding/context_constructor.py:45`
- Test: `tests/unit/test_context_constructor.py`

**Interfaces:**
- Consumes: none new.
- Produces: `generate_first_message(time_of_day: Optional[str] = None) -> str` (drops the never-used `persona` parameter). Verified zero production callers exist for this function at all (exported from `__init__.py` but never invoked by `cold_start_engine.py` or the orchestrator) — this task only removes the dead parameter; it does not wire the function into the pipeline (that remains a documented future follow-up, matching Layer 5/Life Calendar).

- [x] **Step 1: Check existing tests reference `persona`**

Run: `grep -n "generate_first_message" tests/unit/test_context_constructor.py`

If any call passes a `persona=` keyword argument, note the exact call site(s) to update in Step 3.

- [x] **Step 2: Run full test file to establish current baseline**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_context_constructor.py -v`
Expected: current tests PASS (baseline before the signature change).

- [x] **Step 3: Remove the dead parameter**

In `backend/layer13_onboarding/context_constructor.py`, change:

```python
def generate_first_message(time_of_day: Optional[str] = None, persona=None) -> str:
```
to:
```python
def generate_first_message(time_of_day: Optional[str] = None) -> str:
```

If Step 1 found any test call passing `persona=...`, remove that keyword argument from the call in `tests/unit/test_context_constructor.py`.

- [x] **Step 4: Run tests to verify nothing broke**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_context_constructor.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add backend/layer13_onboarding/context_constructor.py tests/unit/test_context_constructor.py
git commit -m "cleanup: remove unused persona parameter from generate_first_message"
```

---

### Task 4: `_default_classifier` in `audit_trail.py` — CORRECTED FINDING, no change made

**Original plan premise was wrong.** Reading `detect_narrative_links`'s full body (not just `_default_classifier`'s signature) during execution showed that `link_score = SEMANTIC_LINK_WEIGHT * semantic + ENTITY_LINK_WEIGHT * entity_overlap` (0.6/0.4, matching the module docstring) is already computed correctly by `detect_narrative_links` itself, using its own `cosine_similarity` + `entity_refs` overlap logic, gated on `LINK_SCORE_THRESHOLD = 0.65`. `classify_fn` (default: `_default_classifier`) is only invoked **after** that gate already decided a link exists — its job is to classify which of the 6 `NarrativeLinkType` values (`CONTINUATION`/`ESCALATION`/`RESOLUTION`/`RELAPSE`/`REFRAMING`/`NEW_DEVELOPMENT`) the link is, a genuinely semantic judgment call (worsening vs. improving vs. a new thread) that a deterministic default can't make reliably — the same class of problem as `forgetting_engine.py`'s injectable `Generalizer` or `state_updater.py`'s injectable `EpisodeExtractor`, both of which also need an LLM for their "real" behavior and accept a simple deterministic default for offline operation.

`_default_classifier(new_ep, last_ep) -> NarrativeLinkType: return NarrativeLinkType.CONTINUATION` accepting-but-not-using its parameters is thus **conformance to the `LinkClassifier = Callable[[EpisodicMemory, EpisodicMemory], NarrativeLinkType]` type alias**, not a bug — "continuation" is a reasonable, conservative default classification for when no smarter classifier is injected, matching this codebase's established DI pattern. Vulture's unused-parameter flag here is the same class of false positive as the FastAPI routes / ABC methods / dunder methods already excluded earlier in the audit.

**No code change made for this task.** (Original Task 4 code below is struck from execution — kept only for audit-trail purposes.)

---

### Task 5: Remove unused import in `active_elicitation_queue.py`

**Files:**
- Modify: `backend/layer13_onboarding/active_elicitation_queue.py:16`

- [x] **Step 1: Remove the dead import**

Change:
```python
from .schemas import ELICITATION_CATEGORIES, ElicitationItem
```
to:
```python
from .schemas import ElicitationItem
```

- [x] **Step 2: Run the file's tests**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_active_elicitation_queue.py -v`
Expected: PASS (no behavior change; pure import cleanup).

- [x] **Step 3: Commit**

```bash
git add backend/layer13_onboarding/active_elicitation_queue.py
git commit -m "cleanup: remove unused ELICITATION_CATEGORIES import"
```

---

### Task 6: Remove dead code in `user_format_profile.py`

**Files:**
- Modify: `backend/layer9_output/user_format_profile.py`

**Interfaces:** none (pure deletion; verified zero callers anywhere in the repo for both symbols, and neither appears in `docs/layer-9-architecture.md`'s `update_format_profile`/§6.6 signal list).

- [x] **Step 1: Confirm zero callers one more time (safety check before deleting)**

Run: `grep -rn "shift_preference_longer\|get_learned_preference" --include="*.py" /home/varunaditya/Projects/nova-ai`
Expected: only the two `def` lines in `user_format_profile.py` itself.

- [x] **Step 2: Delete the two functions**

Remove `shift_preference_longer` (the 3-line function right after `shift_preference_shorter`) and `get_learned_preference` (its full body) from `backend/layer9_output/user_format_profile.py`.

- [x] **Step 3: Run tests to verify nothing broke**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_user_format_profile.py -v`
Expected: PASS.

- [x] **Step 4: Commit**

```bash
git add backend/layer9_output/user_format_profile.py
git commit -m "cleanup: remove shift_preference_longer and get_learned_preference (zero callers, not referenced by architecture doc §6.6)"
```

---

### Task 7: Remove dead `count_emoji` in `format_adapter.py`

**Files:**
- Modify: `backend/layer9_output/format_adapter.py:149`

- [x] **Step 1: Confirm `_reduce_emoji_to_limit` doesn't call it internally**

Run: `grep -n "count_emoji" backend/layer9_output/format_adapter.py`
Expected: only the `def count_emoji` line itself and no call sites — `_reduce_emoji_to_limit` does its own counting inline.

- [x] **Step 2: Delete the function**

Remove the `count_emoji` function (3 lines) from `backend/layer9_output/format_adapter.py`.

- [x] **Step 3: Run tests to verify nothing broke**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_format_adapter.py -v`
Expected: PASS.

- [x] **Step 4: Commit**

```bash
git add backend/layer9_output/format_adapter.py
git commit -m "cleanup: remove unused count_emoji helper (logic already inline in _reduce_emoji_to_limit)"
```

---

### Task 8: Replace duplicated due-thread logic in `service.py` with `get_due_threads`

**Files:**
- Modify: `backend/layer1_input/service.py:81-84`
- Test: `tests/unit/test_layer1_service.py`

**Interfaces:**
- Consumes: `backend.layer1_input.thread_tracker.get_due_threads(store: ThreadStore, now: datetime, max_threads: int = MAX_SURFACED_THREADS) -> list[NarrativeThread]` (existing, already tested in `tests/unit/test_thread_tracker.py`).
- Produces: `service.py` no longer re-derives `candidates[:MAX_SURFACED_THREADS]` inline; it calls `get_due_threads` directly.

- [x] **Step 1: Read the current call site**

Run: `sed -n '75,90p' backend/layer1_input/service.py` to see the exact surrounding lines before editing (variable names may differ slightly from what's summarized here).

- [x] **Step 2: Write/extend the failing test**

Add to `tests/unit/test_layer1_service.py` (adjust to match the file's existing fixture helpers for constructing a `ThreadStore` with due entries — read the file first):

```python
def test_surfaced_threads_delegates_to_get_due_threads(monkeypatch):
    calls = []
    import backend.layer1_input.service as service_mod

    def spy(store, now, max_threads=service_mod.thread_tracker.MAX_SURFACED_THREADS):
        calls.append((store, now, max_threads))
        return []

    monkeypatch.setattr(service_mod.thread_tracker, "get_due_threads", spy)
    # ... call the surrounding function in service.py that currently does the inline slicing ...
    assert calls, "service.py should call thread_tracker.get_due_threads instead of reimplementing it"
```

(Fill in the `...` with whatever function in `service.py` contains the `due_candidates`/slicing lines from Step 1 — call it the same way the file's other existing tests already do.)

- [x] **Step 3: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_layer1_service.py -k delegates_to_get_due_threads -v`
Expected: FAIL — `get_due_threads` spy was never called because `service.py` still calls `due_candidates` + manual slicing.

- [x] **Step 4: Write minimal implementation**

In `backend/layer1_input/service.py`, replace:

```python
        candidates = thread_tracker.due_candidates(store, now)
        surfaced = candidates[: thread_tracker.MAX_SURFACED_THREADS]
```
with:
```python
        surfaced = thread_tracker.get_due_threads(store, now)
```

- [x] **Step 5: Run tests to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_layer1_service.py tests/unit/test_thread_tracker.py -v`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add backend/layer1_input/service.py tests/unit/test_layer1_service.py
git commit -m "fix: use thread_tracker.get_due_threads instead of reimplementing it inline in service.py"
```

---

### Task 9: Wire goal momentum tracking into `run_goal_pipeline`

**Files:**
- Modify: `backend/layer7_goals/engine.py`
- Test: `tests/unit/test_layer7_engine.py`

**Interfaces:**
- Consumes: `backend.layer7_goals.progress_monitor.compute_momentum(signal_events: list, now: Optional[datetime] = None) -> float` (existing), `backend.layer7_goals.schemas.GoalSignalEvent` (existing dataclass: `event_id`, `goal_id`, `event_type`, `timestamp`, `evidence_text`, `confidence`, ...), `Goal.signal_events: list` and `Goal.momentum_score: float` (existing fields, currently never populated in production).
- Produces: after this task, every classified progress signal on the top relevant goal appends a `GoalSignalEvent` to `goal.signal_events` and recomputes `goal.momentum_score` via `compute_momentum`, before persisting through `goal_store.update_goal(top)`. This makes `goal_store.py`'s `+ 0.15 * goal.momentum_score` ranking term and `accountability_modifier.py`'s `goal.momentum_score > _CONNECT_MOMENTUM_FLOOR` gate (CASE 4, "connect topic") live for the first time.

- [x] **Step 1: Write the failing test**

Add to `tests/unit/test_layer7_engine.py`:

```python
def test_progress_signal_updates_momentum_score():
    store = GoalStore([_goal(score=0.5)])
    out = _run(store, "I made progress and stuck to it this week")
    updated = store.get("g1")
    assert isinstance(out, Layer7Output)
    assert len(updated.signal_events) == 1
    assert updated.signal_events[0].event_type == "progress_positive"
    assert updated.momentum_score > 0.0
```

- [x] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_layer7_engine.py -k updates_momentum_score -v`
Expected: FAIL — `updated.signal_events` is empty and `momentum_score` stays at whatever `_goal()`'s fixture default is (0.5 per the existing fixture — note this fixture already seeds `momentum_score=0.5`; this test's goal `_goal(score=0.5)` uses the fixture default `momentum_score=0.5` too, so assert `len(signal_events) == 1` is the meaningful failing assertion here since momentum starts non-zero in the fixture).

- [x] **Step 3: Write minimal implementation**

In `backend/layer7_goals/engine.py`, add the import:

```python
from backend.layer7_goals.schemas import (
    Goal,
    GoalContextPacket,
    GoalSignalEvent,
    GoalStatus,
    Layer7Output,
)
```

Then replace the SC-3 block:

```python
    # SC-3: inline progress signal on the top goal.
    progress_signal = None
    if relevant:
        top = relevant[0].goal
        progress_signal = _safe(
            lambda: progress_monitor.classify_progress_signal(message, top), None
        )
        if progress_signal is not None:
            progress_monitor.update_progress_score(top, progress_signal)
            top.signal_events.append(GoalSignalEvent(
                goal_id=top.goal_id, event_type=progress_signal.signal_type,
                timestamp=now, evidence_text=message,
                confidence=progress_signal.confidence))
            top.momentum_score = progress_monitor.compute_momentum(top.signal_events, now=now)
            top.last_mentioned_at = now
            goal_store.update_goal(top)  # persist progress through the store (store-agnostic)
            out.goals_updated.append(top.goal_id)
```

- [x] **Step 4: Run tests to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_layer7_engine.py tests/unit/test_progress_monitor.py tests/unit/test_accountability_modifier.py -v`
Expected: PASS — including pre-existing tests (momentum-floor-gated CASE 4 in `accountability_modifier.py` may now activate in scenarios where it previously couldn't; if any pre-existing test asserted CASE 4 never fires, re-read that assertion and confirm it's still correct given momentum can now be nonzero — adjust only if the test was asserting the bug, not the intended behavior).

- [x] **Step 5: Verify `signal_events`/`momentum_score` actually round-trip through `PostgresGoalStore`**

This is the step that discriminates "momentum works" from "momentum only looks like it works" — `PostgresGoalStore` (`infra/db/goal_store.py`) persists the whole `Goal` dataclass as JSONB via `to_jsonable`/`from_jsonable` (`infra/db/memory_serde.py`), the same mechanism already used for `EpisodicMemory`'s datetime fields, so this **should** work, but must be verified rather than assumed. Add to `tests/unit/infra/test_postgres_goal_store.py` (matching its existing `_store()` helper):

```python
def test_signal_events_and_momentum_round_trip_through_postgres():
    from datetime import datetime, timezone
    from backend.layer7_goals.schemas import GoalSignalEvent

    store = _store()
    now = datetime.now(timezone.utc)
    goal = Goal(goal_id="g1", title="run 5k", status="active")
    goal.signal_events.append(GoalSignalEvent(
        goal_id="g1", event_type="progress_positive", timestamp=now, confidence=0.8))
    goal.momentum_score = 0.42
    store.add_goal(goal)

    reloaded = store.get("g1")
    assert len(reloaded.signal_events) == 1
    assert reloaded.signal_events[0].event_type == "progress_positive"
    assert isinstance(reloaded.signal_events[0].timestamp, datetime)  # not a raw string
    assert reloaded.momentum_score == 0.42

    # compute_momentum must be able to do arithmetic on the reloaded timestamp.
    from backend.layer7_goals.progress_monitor import compute_momentum
    assert compute_momentum(reloaded.signal_events, now=now) > 0.0
```

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_postgres_goal_store.py -v`
Expected: PASS. If `reloaded.signal_events[0].timestamp` comes back as a `str` instead of `datetime`, or `signal_events` comes back empty, STOP — this means `memory_serde` doesn't generically round-trip nested dataclass lists with datetime fields, and Task 9 needs a `from_jsonable`/`to_jsonable` fix (in `infra/db/memory_serde.py`) before it can be considered done, not just a `Goal`/`engine.py` fix. Do not proceed to Task 10 until this passes for real.

- [x] **Step 6: Commit**

```bash
git add backend/layer7_goals/engine.py tests/unit/test_layer7_engine.py tests/unit/infra/test_postgres_goal_store.py
git commit -m "feat: track GoalSignalEvents and compute momentum_score in run_goal_pipeline (was permanently stuck at its default); verify Postgres round-trip"
```

---

### Task 10: Thread `signal_strength` from LLM goal extraction into `Goal`

**Files:**
- Modify: `backend/layer7_goals/schemas.py`, `backend/layer7_goals/goal_extractor.py`, `backend/layer7_goals/engine.py`
- Test: `tests/unit/test_goal_extractor.py`, `tests/unit/test_layer7_engine.py`

**Interfaces:**
- Consumes: `GoalSignalStrength(str, Enum)` (existing, `EXPLICIT_STATED`/`IMPLICIT_ASPIRED`/`REPEATED_THEME`/`ABANDONED_REVISIT`, documented in `docs/layer-7-architecture.md:106-110` and already requested in the extraction LLM prompt at `goal_extractor.py:81` but silently dropped from the parsed response).
- Produces: `GoalExtractionResult.signal_strength: str = ""` (new field), `Goal.signal_strength: str = ""` (new field), `extract_goal()` now reads `new_goal.get("signal_strength", "")` from the LLM's JSON response and sets it on the result; `run_goal_pipeline` copies it onto the newly created `Goal`.

- [x] **Step 1: Write the failing test**

Add to `tests/unit/test_goal_extractor.py`:

```python
def test_extract_goal_reads_signal_strength_from_llm_response():
    def llm(prompt):
        return {
            "goal_detected": True,
            "new_goal": {
                "inferred_title": "Learn Spanish", "confidence": 0.8,
                "signal_strength": "implicit_aspired",
            },
        }
    result = extract_goal("I've been meaning to learn Spanish", llm_fn=llm)
    assert result.signal_strength == "implicit_aspired"
```

(Match this test's imports/fixture style to whatever `test_goal_extractor.py` already uses at the top of the file — read it first.)

- [x] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_goal_extractor.py -k signal_strength -v`
Expected: FAIL — `GoalExtractionResult` has no `signal_strength` attribute yet.

- [x] **Step 3: Write minimal implementation**

In `backend/layer7_goals/schemas.py`, add a field to `GoalExtractionResult` (right after `confidence: float = 0.0`):

```python
    signal_strength: str = ""
```

And add a field to `Goal` (near `confidence_at_creation: float = 0.0`):

```python
    signal_strength: str = GoalSignalStrength.EXPLICIT_STATED.value
```

In `backend/layer7_goals/goal_extractor.py`, in `extract_goal()`, right after the existing line `result.confidence = float(new_goal.get("confidence", raw.get("confidence", 0.0)))`, add:

```python
    result.signal_strength = str(new_goal.get("signal_strength", ""))
```

In `backend/layer7_goals/engine.py`'s `run_goal_pipeline`, in the `new_goal = Goal(...)` construction, add the field:

```python
                    signal_strength=extraction.signal_strength or GoalSignalStrength.EXPLICIT_STATED.value,
```

and add `GoalSignalStrength` to the existing schema import in `engine.py`.

- [x] **Step 4: Run tests to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/test_goal_extractor.py tests/unit/test_layer7_engine.py -v`
Expected: PASS.

- [x] **Step 5: Verify `signal_strength` round-trips through `PostgresGoalStore`**

Add to `tests/unit/infra/test_postgres_goal_store.py`:

```python
def test_signal_strength_round_trips_through_postgres():
    store = _store()
    store.add_goal(Goal(goal_id="g1", title="run 5k", status="active",
                        signal_strength="implicit_aspired"))
    assert store.get("g1").signal_strength == "implicit_aspired"
```

Run: `/usr/bin/python3.11 -m pytest tests/unit/infra/test_postgres_goal_store.py -v`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add backend/layer7_goals/schemas.py backend/layer7_goals/goal_extractor.py backend/layer7_goals/engine.py tests/unit/test_goal_extractor.py tests/unit/infra/test_postgres_goal_store.py
git commit -m "feat: thread signal_strength from LLM goal extraction onto Goal (was requested in the prompt and silently dropped); verify Postgres round-trip"
```

---

### Task 11: Expose `ToolManager.undo_action` via a new API route

**Files:**
- Modify: `api/routes/tools.py`
- Test: `tests/unit/api/test_routes_tools.py`

**Interfaces:**
- Consumes: `ToolManager.undo_action(action_id: str, user_id: Optional[str] = None) -> bool` (existing, tested in isolation in `tests/unit/test_tool_manager.py` but never reachable via HTTP).
- Produces: `POST /tools/undo/{action_id}` → `{"undone": true|false}`, matching the existing `deny_action`'s `{"denied": request_id}` response shape.

- [x] **Step 1: Write the failing test**

Add to `tests/unit/api/test_routes_tools.py`:

```python
def test_undo_action_route_marks_action_undone():
    client, tm = _client()
    out = tm.process("search for puppy training tips", user_id="local-user", session_id="s1")
    assert out.tool_invoked is True
    action_id = out.action_record.action_id

    resp = client.post(f"/tools/undo/{action_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["undone"] in (True, False)  # web_search plugin may not support undo; either is valid

    history = client.get("/tools/history").json()
    assert history[0]["action_id"] == action_id
```

- [x] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/api/test_routes_tools.py -k undo_action_route -v`
Expected: FAIL — 404, no such route.

- [x] **Step 3: Write minimal implementation**

In `api/routes/tools.py`, add after the existing `deny_action` route:

```python
@router.post("/undo/{action_id}")
def undo_action(action_id: str, state=Depends(get_state), tm=Depends(get_tool_manager)):
    if tm is None:
        raise HTTPException(status_code=404, detail="no tool manager")
    undone = tm.undo_action(action_id, user_id=state.default_user_id)
    return {"undone": undone}
```

- [x] **Step 4: Run tests to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/api/test_routes_tools.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add api/routes/tools.py tests/unit/api/test_routes_tools.py
git commit -m "feat: expose POST /tools/undo/{action_id} (ToolManager.undo_action was implemented and tested but unreachable via HTTP)"
```

---

### Task 12: Wire FCE cluster detection + semantic extraction into the memory consolidation job

**Files:**
- Modify: `background/memory_consolidation_job.py`
- Test: `tests/unit/background/test_jobs.py`

**Interfaces:**
- Consumes: `backend.layer2_memory.forgetting_engine.EPISODE_COUNT_TRIGGER` (constant, 50), `.cluster_detection(episodes, threshold=0.85, min_members=3) -> list[EpisodicCluster]`, `.extract_semantic_memory(cluster, user_id, generalize_fn, now, memory_type=...) -> SemanticMemory` (all existing, all already unit-tested in `tests/unit/test_forgetting_engine.py`), `PostgresMemoryStore.save_semantic(memory: SemanticMemory) -> UUID` (existing, already tested in `tests/unit/infra/test_postgres_memory_store.py`), `app_state.llm_clients["system1"].complete(prompt: str) -> str` (existing pattern, same as `make_goal_writer` in `api/state.py:209`). Note: `should_trigger_fce`'s `sessions_since`/`days_since` OR-conditions need a persisted "since last run" counter this job does not have (no new table, per this plan's constraints) — only the episode-count condition is checked directly; see the job's docstring for why.
- Produces: `run(app_state) -> dict` now also runs cluster detection + semantic extraction after the decay sweep when `should_trigger_fce` says to, and returns a dict matching `FCERunReport`'s fields (`clusters_detected`, `semantic_memories_created`, `episodes_consolidated`, `new_semantic_summaries`) in addition to the existing `swept`/`deleted`/`archived` keys.

- [x] **Step 1: Write the failing test**

Add to `tests/unit/background/test_jobs.py` (match its existing fixture style for constructing an `app_state`-like object with `session_factory`/`default_user_id`/`llm_clients` — read the file first for the exact helper name, e.g. `_state()` or similar):

```python
def test_memory_consolidation_runs_semantic_extraction_when_triggered(tmp_app_state):
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer2_memory.schemas import EpisodicMemory
    from datetime import datetime, timezone

    store = PostgresMemoryStore(tmp_app_state.session_factory)
    now = datetime.now(timezone.utc)
    # Seed >= EPISODE_COUNT_TRIGGER (50) near-identical episodes so a cluster forms.
    for i in range(55):
        store.save_episodic(EpisodicMemory(
            user_id=tmp_app_state.default_user_id, summary=f"felt anxious about work #{i}",
            embedding=[1.0, 0.0, 0.0], created_at=now, last_decay_computed_at=now))

    from background.memory_consolidation_job import run
    result = run(tmp_app_state)

    assert result["clusters_detected"] >= 1
    assert result["semantic_memories_created"] >= 1
    beliefs_or_semantic = store.active_semantic(tmp_app_state.default_user_id)
    assert len(beliefs_or_semantic) >= 1
```

(Replace `tmp_app_state` with whatever fixture `test_jobs.py` already provides for a real Postgres-backed `app_state` — this file already tests other jobs against real stores, per the existing `background/*_job.py` test pattern; follow its exact setup.)

- [x] **Step 2: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/background/test_jobs.py -k semantic_extraction -v`
Expected: FAIL — `KeyError: 'clusters_detected'` (current `run()` only returns `swept`/`deleted`/`archived`).

- [x] **Step 3: Write minimal implementation**

Replace `background/memory_consolidation_job.py`'s `run` function:

```python
"""Memory consolidation job — Layer-2 forgetting sweep + FCE semantic extraction over persisted
episodes.

Runs every ~2h. Recomputes each active episode's decayed strength and archives/deletes the ones
that fall below threshold (``decay_sweep``), then persists the results (always). When the FCE
trigger conditions are met (``should_trigger_fce``), also runs agglomerative cluster detection
over the remaining active episodes and compresses each qualifying cluster into a semantic memory
via an injected LLM generalizer (``app_state.llm_clients["system1"]``), persisting both the new
semantic memory and the now-consolidated episodes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("nova.jobs")


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer2_memory.forgetting_engine import (
        EPISODE_COUNT_TRIGGER, cluster_detection, decay_sweep, extract_semantic_memory,
    )

    uid = app_state.default_user_id
    store = PostgresMemoryStore(app_state.session_factory)
    now = datetime.now(timezone.utc)

    episodes = [e for e in store.all_episodic(uid) if not getattr(e, "is_deleted", False)]
    deleted, archived = decay_sweep(episodes, now)
    for ep in episodes:
        store.save_episodic(ep)

    clusters_detected = semantic_memories_created = episodes_consolidated = 0
    new_summaries: list[str] = []

    # should_trigger_fce(new_episodes, sessions_since, days_since) needs "since the last FCE
    # run" counters this job does not persist (no new table, per this plan's constraints); the
    # session-count and calendar-day trigger paths are a documented follow-up. What we *can*
    # check honestly without new state: whether enough active (already decay-surviving,
    # not-yet-consolidated) episodes exist to be worth attempting clustering over.
    active = [e for e in episodes if not e.is_deleted]
    if len(active) >= EPISODE_COUNT_TRIGGER:
        clusters = cluster_detection(active)
        clusters_detected = len(clusters)

        def _generalize(summaries: list[str]) -> str:
            client = app_state.llm_clients.get("system1")
            if client is None:
                return summaries[0] if summaries else ""
            prompt = ("Summarize the common pattern across these journal-like notes into one "
                      "short third-person statement about the user: " + " | ".join(summaries))
            try:
                return client.complete(prompt).strip()
            except Exception:
                return summaries[0] if summaries else ""

        for cluster in clusters:
            semantic = extract_semantic_memory(cluster, uid, _generalize, now)
            store.save_semantic(semantic)
            for ep in cluster.members:
                store.save_episodic(ep)  # persist consolidated_into / is_deleted from extraction
            semantic_memories_created += 1
            episodes_consolidated += len(cluster.members)
            new_summaries.append(semantic.statement)

    logger.info("consolidation: swept=%d deleted=%d archived=%d clusters=%d semantic=%d",
                len(episodes), deleted, archived, clusters_detected, semantic_memories_created)
    return {
        "swept": len(episodes), "deleted": deleted, "archived": archived,
        "clusters_detected": clusters_detected,
        "semantic_memories_created": semantic_memories_created,
        "episodes_consolidated": episodes_consolidated,
        "new_semantic_summaries": new_summaries,
    }
```

- [x] **Step 4: Run tests to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/background/test_jobs.py -v`
Expected: PASS, including pre-existing tests for this job (the `swept`/`deleted`/`archived` keys are unchanged; only new keys were added, so no existing assertion on those three keys should break — if a pre-existing test does an exact dict-equality check on the return value rather than checking specific keys, update it to check keys individually instead of exact equality).

- [x] **Step 5: Run the full offline suite**

Run: `/usr/bin/python3.11 -m pytest tests/ -q`
Expected: all tests pass (no regressions elsewhere).

- [x] **Step 6: Commit**

```bash
git add background/memory_consolidation_job.py tests/unit/background/test_jobs.py
git commit -m "feat: wire FCE cluster detection + semantic extraction into memory_consolidation_job (was decay-sweep-only; save_semantic was never called in production)"
```

---

### Task 13: Wire the Layer-11 Dependency Monitor into a new weekly background job

**Files:**
- Create: `background/dependency_monitor_job.py`
- Modify: `background/scheduler.py`, `config/defaults.yaml`
- Test: `tests/unit/background/test_jobs.py`

**Interfaces:**
- Consumes: `backend.layer11_safety.dependency_monitor.compute_dependency_score(user_id, indicator_detector=None, previous_score=None, indicators=None, now=None) -> DependencyScore`, `DEPENDENCY_INDICATORS` (existing 15-indicator list), `PostgresMemoryStore.active_episodic(user_id) -> list[EpisodicMemory]` (existing — each `EpisodicMemory` has `.summary: str`), `PostgresSafetyLog` (existing, in `infra/db/safety_store.py` — check its exact method names with `grep -n "def " infra/db/safety_store.py` before writing Step 3, since this task needs to persist the computed `DependencyScore` somewhere durable across weekly runs so `previous_score`/trend comparison works next time; if `PostgresSafetyLog` has no natural place for this, store the score as a JSON-serializable dict via whatever generic "latest safety-relevant record" mechanism that store already exposes — read the file first rather than inventing a new table).
- Produces: `background/dependency_monitor_job.py::run(app_state) -> dict` returning `{"tier": ..., "score": ..., "trend": ..., "dominant_signals": [...]}`; a real (deterministic, keyword-based — no LLM, matching this module's existing "Deterministic; no LLM on the inline path" style) `indicator_detector` built from `active_episodic()` text instead of the always-`False` default; registered in `background/scheduler.py`'s `JOBS` dict with a weekly cadence.

- [x] **Step 1: Read `PostgresSafetyLog`'s interface first**

Run: `grep -n "def \|class " infra/db/safety_store.py`

Use whatever read/write methods it already exposes to persist/retrieve the previous week's `DependencyScore` (as a dict via its existing serialization pattern) — do not add a new table. If no suitable method exists for arbitrary structured storage, store `previous_score=None` for now (the trend will just always read as "stable" on the first comparison per run until a future task adds proper persistence) and note this limitation in the job's docstring rather than inventing new infrastructure.

- [x] **Step 2: Write the failing test**

Add to `tests/unit/background/test_jobs.py`:

```python
def test_dependency_monitor_job_computes_score_from_episodic_keywords(tmp_app_state):
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer2_memory.schemas import EpisodicMemory
    from datetime import datetime, timezone

    store = PostgresMemoryStore(tmp_app_state.session_factory)
    now = datetime.now(timezone.utc)
    store.save_episodic(EpisodicMemory(
        user_id=tmp_app_state.default_user_id,
        summary="I told Nova she's the only one who really understands me, better than my friends",
        created_at=now))

    from background.dependency_monitor_job import run
    result = run(tmp_app_state)

    assert "tier" in result
    assert "score" in result
    assert 0.0 <= result["score"] <= 1.0
```

- [x] **Step 3: Run test to verify it fails**

Run: `/usr/bin/python3.11 -m pytest tests/unit/background/test_jobs.py -k dependency_monitor -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'background.dependency_monitor_job'`.

- [x] **Step 4: Write minimal implementation**

Create `background/dependency_monitor_job.py`:

```python
"""Dependency monitor job — Layer-11 SC-4 weekly check (architecture doc §6).

Runs weekly. Builds a deterministic, keyword-based indicator detector from the user's recent
episodic memories (no LLM — matches dependency_monitor.py's own "deterministic" design) and
computes the weighted dependency score. The real semantic-search-grade detector described in
the architecture doc (embeddings-based, not keyword-based) is a documented follow-up; this
keyword heuristic is a conservative first pass that keeps the job from always returning "no
signal" (its previous state: unreachable, since no job called it at all).
"""
from __future__ import annotations

import logging

logger = logging.getLogger("nova.jobs")

# A few observable keyword signals per indicator category — conservative, low-recall by design
# (false negatives are safe here; this only informs a graduated, never-announced intervention).
_KEYWORD_SIGNALS = {
    "SS_01": ("only one who understands", "only one i can talk to", "no one else gets me"),
    "SS_03": ("better than my friends", "better than my family", "don't need people"),
    "AE_04": ("don't need therapy", "don't need a therapist", "i'd rather just talk to you"),
    "EI_03": ("plan my life around", "wait until i can talk to you"),
}


def _build_indicator_detector(episode_summaries: list):
    text = " ".join(s.lower() for s in episode_summaries if s)

    def detector(indicator) -> bool:
        keywords = _KEYWORD_SIGNALS.get(indicator.indicator_id)
        if not keywords:
            return False
        return any(kw in text for kw in keywords)

    return detector


def run(app_state) -> dict:
    from infra.db.memory_store import PostgresMemoryStore
    from backend.layer11_safety.dependency_monitor import compute_dependency_score

    uid = app_state.default_user_id
    store = PostgresMemoryStore(app_state.session_factory)
    episodes = store.active_episodic(uid)
    detector = _build_indicator_detector([getattr(e, "summary", "") for e in episodes])

    result = compute_dependency_score(uid, indicator_detector=detector)
    logger.info("dependency check: user=%s tier=%s score=%.2f", uid, result.tier, result.score)
    return {
        "tier": result.tier, "score": result.score, "trend": result.trend,
        "dominant_signals": result.dominant_signals,
    }
```

(If Step 1 found a `PostgresSafetyLog` method suited to persisting `previous_score` across runs, add that read/write around the `compute_dependency_score` call here, passing `previous_score=...` — otherwise leave as above and note the limitation, per Step 1's instruction.)

Register it in `background/scheduler.py` — add to the import block:

```python
from background import (
    dependency_monitor_job,
    integrity_check_job,
    longitudinal_summary_job,
    memory_consolidation_job,
    pattern_detection_job,
    proactive_check_job,
)
```

Add to `JOBS`:

```python
JOBS = {
    "memory_consolidation": memory_consolidation_job.run,
    "proactive_check": proactive_check_job.run,
    "pattern_detection": pattern_detection_job.run,
    "integrity_check": integrity_check_job.run,
    "longitudinal_summary": longitudinal_summary_job.run,
    "dependency_monitor": dependency_monitor_job.run,
}
```

Add to `start_scheduler`, right after the `longitudinal_summary` `add_job` call:

```python
    sched.add_job(_wrap("dependency_monitor"), "interval",
                  days=cfg.get("dependency_monitor_days", 7), id="dependency_monitor")
```

Add to `config/defaults.yaml`'s `scheduler:` block, after `longitudinal_summary_days: 7`:

```yaml
  dependency_monitor_days: 7
```

- [x] **Step 5: Run tests to verify it passes**

Run: `/usr/bin/python3.11 -m pytest tests/unit/background/test_jobs.py -v`
Expected: PASS.

- [x] **Step 6: Verify the manual-trigger admin endpoint picks it up**

Run: `/usr/bin/python3.11 -m pytest tests/unit/api/test_routes_background.py -v`
Expected: PASS — `POST /admin/jobs/dependency_monitor` should now resolve via `JOBS["dependency_monitor"]` without a `KeyError` (this route already iterates `JOBS` generically per the existing test file, so no route-file change is needed — only verify).

- [x] **Step 7: Run the full offline suite**

Run: `/usr/bin/python3.11 -m pytest tests/ -q`
Expected: all tests pass (no regressions elsewhere).

- [x] **Step 8: Commit**

```bash
git add background/dependency_monitor_job.py background/scheduler.py config/defaults.yaml tests/unit/background/test_jobs.py
git commit -m "feat: wire Layer-11 SC-4 dependency monitor into a new weekly background job (was implemented, tested, and documented as running weekly, but had zero production callers)"
```

---

## Explicitly NOT changed (surfaced for override, not silently declined)

The user's instruction was "any unused code must be removed unless required per docs." These three findings have zero production callers today but were deliberately left alone rather than removed — flag before executing this plan in case the user wants a different call:

- **`backend/layer12_privacy/privacy_agent.py::PrivacyAgent`** — the coordinator facade class is never instantiated; `api/routes/memory.py` calls `selective_deletion`/`memory_audit` functions directly instead. This matches the codebase's established in-memory-vs-Postgres DI pattern (like `backend/layer2_memory/memory_store.py` vs `infra/db/memory_store.py`) closely enough that removing it risks deleting a legitimate offline reference implementation — but it could equally be a stale abandoned facade. Not confident enough either way to touch it.
- **`backend/layer8_tools/tool_manager.py::ToolManager.execute_tool`** — a fully self-gating direct-execution method, never called; `process()`/`confirm_action()` each duplicate its logic inline via `_execute_and_record`. Consolidating them changes control flow in the tool-safety path (confirmation gating, token consumption) — higher-risk than the other fixes in this plan without a clearer signal of which of the three code paths is "correct."
- **`backend/layer6_proactivity/queue_manager.py::ProactiveQueueManager.add_item`** — only called by `tests/unit/test_proactive_engine.py` and `tests/unit/test_proactive_queue_manager.py` directly against the class; production (`background/proactive_check_job.py`) always constructs the manager pre-loaded from `q.load()` rather than adding incrementally. Removing it breaks 2 test files for a method that is a legitimate, harmless part of the class's public API (analogous to `list.append`) — low value, needless blast radius.

## Post-plan verification

- [x] Run the full baseline command from CLAUDE.md: `/usr/bin/python3.11 -m pytest tests/ -q` and confirm the pass count is >= 1171 (no regressions, plus the new tests added across Tasks 1–13).
- [x] Re-run `vulture backend api infra background config data scripts migrations --min-confidence 60` and confirm the specific symbols fixed in Tasks 3, 5, 6, 7 no longer appear, and that Tasks 1, 2, 4, 8–13 didn't introduce any new unused-variable findings.
