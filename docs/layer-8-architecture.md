# Layer 8 — Tools & Actions
## NovaAI Architecture | Complete Technical Specification

---

## 1. What This Layer Is

Layer 8 is the **action layer**. Every layer before it makes Nova understand, remember, and
respond. Layer 8 is what lets Nova *act on the world* on the user's behalf — put an event on a
calendar, draft an email, capture a note, set a reminder, look something up. It is the bridge
between conversation and consequence.

Because actions have consequences, the defining concern of this layer is not capability but
**control**. A companion that can send email, modify calendars, and delete data is only
trustworthy if the user is always, demonstrably in charge of what it does. So Layer 8 is built
around three guarantees:

1. **High-risk actions require explicit confirmation.** Low-risk, reversible actions may run
   immediately; anything that reaches outside Nova or cannot be undone is gated.
2. **Every action is recorded and inspectable.** The audit trail is append-only — undoing an
   action is itself recorded, never erased.
3. **Nothing is destroyed silently.** Deletes are logical (archived), so they can be undone.
   The single exception is a sent email, which genuinely cannot be recalled — and the system is
   honest about that.

> **Scope / reconciliation note.** An earlier revision of this document described Layer 8 as a
> "Crisis Detection & Safety Engine." That was a layer-numbering mismatch. Crisis detection,
> safeguarding, escalation, and dependency monitoring are fully specified and owned by
> **Layer 11** (`docs/layer-11-architecture.md`). Layer 8 is Tool Use & Actions, matching the
> code scaffold (`backend/layer8_tools/`), the database model (`infra/db/models/tools.py`), and
> `config/layer8.yaml`. This document has been rewritten accordingly.

Layer 8 contains **four sub-components plus a plugin set**:

- **SC-1: Tool Manager** — orchestrates the full workflow and routes to plugins
- **SC-2: Confirmation Gate** — maps an action's risk profile to a confirmation tier
- **SC-3: Parameter Resolver** — detects missing parameters; asks one clarifying question/turn
- **SC-4: Action Recorder** — the append-only, auditable execution log
- **Plugins** — `ToolPlugin` implementations on a uniform, swappable interface

---

## 2. Architecture Overview

```
A user message that asks Nova to DO something
                    │
                    ▼
   ┌─────────────────────────────────────────────┐
   │  SC-1: Tool Manager (orchestrator)          │
   │                                             │
   │  1. detect_intent  ───────────────────────► ToolIntent (or None → no tool)
   │  2. resolve params (SC-3) ────────────────► missing? → ONE clarifying question
   │  3. confirmation gate (SC-2) ─────────────► SOFT/HARD? → ConfirmationRequest
   │  4. execute via plugin (uniform interface)                                   │
   │  5. record (SC-4) ────────────────────────► ActionRecord (append-only)       │
   └─────────────────────────────────────────────┘
                    │
                    ▼
              ToolUseOutput
        (result + action record, or
         a clarification / confirmation
         request handed back to Layer 4/9)
```

**Execution position.** Layer 8 is invoked during response generation (Layer 4) when the user's
message expresses an intent to act. It is *not* on the safety-critical path: if Layer 11 detects
a crisis, the crisis response takes over and tool use is suppressed along with the rest of the
normal pipeline. A failure anywhere in Layer 8 degrades to "no action taken" and is recorded —
it never raises into the pipeline or blocks a response.

---

## 3. Schemas

```python
class ConfirmationTier(str, Enum):  # how much assent an action needs
    AUTO = "auto"   # low risk, reversible — execute immediately
    SOFT = "soft"   # ask, but a non-objection / timeout proceeds
    HARD = "hard"   # require explicit confirmation

class RiskLevel(str, Enum):    LOW / MEDIUM / HIGH
class ActionType(str, Enum):   READ / SEARCH / CREATE / UPDATE / DELETE / SEND
class ToolOutcome(str, Enum):  SUCCESS / FAILURE / PENDING / CANCELLED

class Capability:                      # how a plugin describes one operation
    operation: str                     # e.g. "create_event", "send"
    action_type: str                   # drives the base confirmation tier
    description: str
    default_tier: Optional[str]        # plugin override; None → derive from action_type
    reversible: bool
    external_impact: bool              # touches systems outside Nova
    risk_level: str
    required_params: list[str]

class ToolIntent:        tool_name, operation, action_type, parameters, parameters_missing,
                         confidence, raw_text
class ParameterGap:      parameter_name, description, required, prompt_hint
class ConfirmationRequest: request_id, tool_name, action_type, action_description, tier,
                           risk_level, reversible, parameters, created_at
class ValidationResult:  valid: bool, errors: list[str]
class ToolResult:        tool_name, operation, outcome, result_summary, data, error_message,
                         undo_token
class ActionRecord:      action_id, tool_name, operation, action_type, parameters, outcome,
                         result_summary, error_message, user_id, user_session_id,
                         linked_episodic_memory_id, undoable, undo_token, undone, timestamp
class ToolUseOutput:     tool_invoked, intent, confirmation_request, clarification_question,
                         result, action_record
```

The key design move is **capability-driven policy**: each plugin declares its operations as
`Capability` objects, and the gate and resolver read risk/reversibility/required-params off the
capability rather than hard-coding per-tool rules. Adding a plugin requires no changes to the
gate or resolver.

---

## 4. Sub-Component 2 — Confirmation Gate

### 4.1 Tiers

- **AUTO** — execute immediately, no user-in-the-loop (web search, read-only queries).
- **SOFT** — surface the action; a non-objection proceeds (draft email, create note/event).
- **HARD** — require explicit confirmation before executing (send email, delete event).

`requires_user_confirmation(tier)` is `True` for SOFT and HARD.

### 4.2 Base tier per action verb

```
read → AUTO   search → AUTO   create → SOFT   update → SOFT   delete → HARD   send → HARD
```

### 4.3 Baseline + intrinsic floors

```python
tier = plugin.default_tier or ACTION_TIER_BASE[action_type]   # plugin tier is authoritative baseline
# intrinsic escalation floors — derived from the action, not the plugin; can only raise:
if risk_level == HIGH:           tier = max(tier, HARD)
if not reversible and external:  tier = max(tier, HARD)
elif not reversible:             tier = max(tier, SOFT)
```

A plugin's declared `default_tier` is **authoritative as the baseline** — it knows its own
operation's stakes, so a reversible, low-stakes action (e.g. a reminder delete) may be AUTO even
though DELETE defaults to HARD. On top of that baseline sit **intrinsic floors** that a plugin
can never lower: high risk, irreversibility, and especially irreversible actions that reach
outside Nova (→ always HARD). The gate can relax a verb's default *downward* for genuinely safe
operations, but never below a safety floor. When in doubt, ask.

### 4.4 ConfirmationRequest assembly

`get_confirmation_request(...)` packages the tool, action verb, a human-readable description,
the computed tier, risk, reversibility, and parameters, with a generated `request_id`, to be
surfaced to the user through Layer 9.

---

## 5. Sub-Component 1 — Tool Manager

The orchestrator and the single entry point. `process(message, user_id, ...)`:

1. **detect_intent** — via an injected `intent_fn` (an LLM in production) with a keyword
   fallback so the layer works offline. Returns `None` → `ToolUseOutput(tool_invoked=False)`.
2. **route** — resolve the plugin; if absent / unsupported operation, no tool is invoked.
3. **resolve params (SC-3)** — if a required parameter is missing, short-circuit with exactly
   one `clarification_question`.
4. **gate (SC-2)** — compute the tier from the capability; if SOFT/HARD, register a bound
   confirmation token and short-circuit with a `ConfirmationRequest`.
5. **execute + record** — for AUTO, call `plugin.execute(...)`, then record via SC-4. A gated
   action executes only when its token is presented back via `confirm_action`.

`confirm_action(request_id, user_id)` executes the action a token was issued for; it is
ownership-checked and single-use. `execute_tool(tool_name, operation, parameters, ...,
confirmation_id=None)` is the direct path — **fail-closed**: an AUTO operation runs, but a gated
operation without a valid matching token is refused. `undo_action(action_id, user_id)` looks up
the record's `undo_token`, refuses if another user owns the action, dispatches to that plugin's
`undo()`, and marks the record undone. The manager never performs actions itself — it routes
through the uniform plugin interface, which is what makes plugins swappable.

### 5.1 Confirmation security model

Confirmation is a **bound, single-use capability token**, never a trusted boolean:

- When a SOFT/HARD action is gated, `process` records a pending confirmation whose `request_id`
  is bound to a SHA-256 **fingerprint** of `(tool, operation, parameters, user_id)`.
- Execution requires presenting that `request_id` back (`confirm_action` or `confirmation_id=`).
  The token is validated against the fingerprint and **consumed on use**.
- This closes three vectors together:
  - **Replay** — a consumed token can't be reused.
  - **Confused deputy** — a token issued for action A fails the fingerprint check for action B.
  - **Cross-user use** — `user_id` is part of the fingerprint, so a token can't authorize a
    different user's action; a non-owner's confirm attempt is refused *without* consuming it.
- The **direct path is fail-closed** (no side door around the gate), and **undo is
  ownership-checked**.

---

## 6. Sub-Component 3 — Parameter Resolver

When an intent is detected but parameters are incomplete, the resolver:

- **6.2 detect_parameter_gaps** — one `ParameterGap` per absent/empty required parameter.
- **6.3 one question per turn** — `next_clarification` returns a single natural question for the
  first (most critical, in declaration order) gap, or `None` when complete. Never a form.
- **6.4 normalize user input** — `resolve_parameter` converts relative dates ("tomorrow") to an
  ISO datetime and trims plain values.
- **6.5 context inference** — `resolve_from_context(intent, capability, infer_fn, ...)` auto-fills
  a parameter only when the injected inference returns confidence ≥ threshold (default 0.85);
  otherwise it leaves the gap for a clarifying question.

---

## 7. Sub-Component 4 — Action Recorder

The auditable log of every execution. It is **append-only**: records are added and their
lifecycle fields (outcome, linked memory, `undone`) are updated in place, but nothing is ever
removed — undoing an action is recorded via `mark_undone`, not erased.

```
record_action(record) -> action_id
record_from_result(result, action_type, ...) -> ActionRecord   # marks undoable iff undo_token
record_action_outcome(action_id, outcome, result_summary, error_message)
link_to_episodic_memory(action_id, memory_id)
mark_undone(action_id)
get_action_history(user_id=None, tool_name=None) -> list[ActionRecord]   # most recent first
```

In production these rows persist via `infra.db.models.tools.ActionRecord` and are inspectable
through Layer 12 (Privacy) and consumed by Layer 10 (Longitudinal) for the life narrative.

---

## 8. Layer 8 Output Contract

```python
class ToolUseOutput:
    tool_invoked: bool
    intent: Optional[ToolIntent]
    confirmation_request: Optional[ConfirmationRequest]  # set when assent is needed
    clarification_question: Optional[str]                # set when a parameter is missing
    result: Optional[ToolResult]
    action_record: Optional[ActionRecord]
```

Exactly one of three terminal states is reached per message: a clarification question, a
confirmation request, or an executed result (with its action record). A message that does not
ask Nova to act yields `tool_invoked=False`.

---

## 9. Plugins

All plugins subclass `ToolPlugin` and implement `capabilities()` + `execute(operation, parameters)`.
The base supplies `validate_parameters` (driven by each capability's `required_params`),
`supports`, `capability_for`, and safe defaults for `undo` (False), `is_healthy` (True), and
`authenticate` (True). External backends and LLMs are injected, so every plugin runs offline;
in-memory stores back the default behavior and **deletes are archived, not dropped**, so they
undo.

| Plugin (§) | Operations | Tiers / notes |
|---|---|---|
| **9.1 Calendar** | create_event, list_events, find_free_time, delete_event | create SOFT (external), list/find AUTO, delete HARD; deletes archived → undo |
| **9.2 Email** | draft, send, read_inbox, list_labels | draft SOFT, **send HARD + irreversible** (undo returns False), reads AUTO |
| **9.3 Notes** | create_note, append_to_note, list_notes, delete_note | create/append AUTO, list AUTO, delete SOFT; deletes archived → undo |
| **9.4 Reminders** | create_reminder, list, complete, snooze, delete | all AUTO (lightweight, fully reversible) |
| **9.5 Web Search** | search, extract_content, synthesize_results | AUTO/read-only; **1-hour result cache**; safety-filters ads/spam; optional LLM synthesis |

---

## 10. Error Handling and Fallbacks

| Failure case | Fallback |
|---|---|
| No tool intent detected | `tool_invoked=False`; normal response continues |
| Unknown tool / unsupported operation | FAILURE result, recorded; no execution |
| Missing required parameter | One clarifying question; no execution |
| Invalid parameters (direct path) | FAILURE result, recorded; plugin never called |
| Gated op on the direct path without a valid token | FAILURE ("confirmation required"), recorded; fail-closed, no execution |
| Confirmation token replayed / for a different action / by a non-owner | Refused; no execution (§5.1) |
| Plugin `execute` raises | Caught → FAILURE result with the error; recorded; pipeline never sees the exception |
| Undo by a non-owner | Returns False; action untouched |
| Undo of an irreversible action (sent email) | Returns False; record stays (audit is append-only) |

**Hard rule:** a failure in Layer 8 degrades to "no action taken," is recorded, and never blocks
or crashes response generation.

---

## 11. Design Principles Summary

1. **The user is always in control.** High-risk actions require explicit confirmation via a
   bound, single-use token (§5.1); the direct path is fail-closed; undo is ownership-checked;
   tool outputs are advisory; the user has final say.
2. **Everything is visible.** Every action is recorded and inspectable; the audit trail is
   append-only — undo is recorded, never erased.
3. **Nothing is destroyed silently.** Deletes are logical (archived) and reversible. The one
   irreversible action — sending an email — is treated as such, honestly.
4. **Policy is data, not branches.** Plugins declare capabilities; the gate and resolver read
   them. New tools need no changes to the orchestration.
5. **Safety lives elsewhere.** Layer 8 acts; Layer 11 protects. When Layer 11 detects a crisis,
   tool use is suppressed with the rest of the normal pipeline.

---

## 12. Implementation Notes (as-built)

- **Module map:** `tool_manager.py` (SC-1), `confirmation_gate.py` (SC-2),
  `parameter_resolver.py` (SC-3), `action_recorder.py` (SC-4), `plugins/base_plugin.py` +
  `plugins/{calendar,email,notes,reminders,web_search}_plugin.py`, `schemas.py`.
- **Dependency injection:** `intent_fn` (intent detection), `search_fn` (web backend),
  `llm_fn` (synthesis), and per-plugin backends are injected callables with safe defaults, so
  the entire layer is testable offline with no network, OAuth, or external services.
- **Capability-driven:** the gate and resolver are plugin-agnostic; they consume `Capability`
  metadata. A plugin's declared tier is the authoritative baseline; intrinsic floors (§4.3) sit
  above it. Adding a plugin is purely additive.
- **Security (§5.1):** confirmation tokens are bound (SHA-256 of tool+operation+parameters+
  user_id), single-use, and ownership-checked; the direct execution path is fail-closed on gated
  tiers; undo refuses non-owners. These harden the orchestrator against confirmation replay,
  confused-deputy, and missing-ownership classes of bug.
- **Deviations from the May-28 scaffold:** none structural — the scaffold already modeled this
  layer correctly (tool_manager, confirmation_gate, parameter_resolver, action_recorder, plugins).
  The only reconciliation was documentary: this architecture doc previously held crisis content
  (now owned by Layer 11) and has been rewritten to specify Tool Use & Actions.
- **Test coverage:** 92 unit tests across `test_confirmation_gate` (14), `test_base_plugin` (8),
  `test_calendar_plugin` (8), `test_email_plugin` (8), `test_notes_plugin` (7),
  `test_reminders_plugin` (6), `test_web_search_plugin` (7), `test_parameter_resolver` (9),
  `test_action_recorder` (8), `test_tool_manager` (17).

---

*This document specifies Layer 8 (Tool Use & Actions) completely. Crisis detection and safety
are specified separately in `docs/layer-11-architecture.md`.*

### Live integration update (2026-07-07) — LLM tool-intent parameter extraction

Tool routing stays on the conservative keyword rules (no false-positive chat hijacking), but a fast
lightweight model (**gemma2:2b**, the `llm.intent` client role) now fills the parameters each
capability declares (`backend/layer8_tools/llm_intent.py`, keyword-gated + `extract_json`-hardened).
Natural-language requests ("email sam@… saying I'll be late") therefore form real SOFT/HARD
confirmations instead of endless clarifications; any LLM/JSON failure degrades to keyword params.
`GET /tools/pending` reports the real tier + reversibility. See `docs/API_REFERENCE.md`.

### Live wiring status (Phase 8 polish pass, 2026-08-04)

The best-audited layer yet: `backend/layer8_tools/` is fully wired end-to-end and no bugs were
found. `ToolManager.process` runs live pre-generation via the orchestrator's `tool_use` hook
(`api/assembly.py`), all five plugins are registered (`api/state.py::build_tool_manager`), the
gemma2:2b parameter-extraction path is wired when an intent client is configured, and all four
`/tools/*` routes (`pending`, `confirm`, `deny`, `undo`) + `history` operate on the real,
Postgres-audited `ToolManager`. The security model (§5.1 — bound SHA-256 fingerprint tokens,
fail-closed direct path, ownership-checked undo) was read line-by-line against the doc's claims
and matches exactly; 92/92 tests pass.

One limitation worth naming rather than fixing: pending confirmations (`ToolManager._pending`)
live only in in-process memory, never persisted — a SOFT/HARD confirmation issued before a
process restart is silently lost (the user would see `404` on `/tools/confirm/{id}`, not a
security issue, just a UX rough edge). This is consistent with the codebase's current
single-process, single-user deployment model (`api/routes/tools.py`'s own docstring already calls
out the "process singleton" assumption) rather than an oversight, so it isn't blocking — but it's
worth knowing if this ever moves to multi-worker or gets a real restart cadence.

### Live wiring status (simplification pass, 2026-08-11)

**File-length cleanup.** `tool_manager.py` (286 lines, the only file in this layer over the cap)
split by responsibility, no behavior change: `intent_routing.py` (keyword routing + intent
coercion), `pending_confirmation.py` (the `Pending` record + fingerprint hash), and
`direct_execution.py` (`execute_tool`'s fail-closed direct path + token consumption) were
extracted, leaving `ToolManager` itself at 185 lines. All existing import paths kept working via
re-exports — `from backend.layer8_tools.tool_manager import _Pending` (used directly by
`tests/unit/api/test_routes_tools.py`) and `api/routes/tools.py`'s `getattr(tm, "_pending", {})`
both still resolve unchanged. Every other module in this layer was already under the cap.

**Minor gap found on re-audit.** `ParameterGap.prompt_hint` is never set — `detect_parameter_gaps`
constructs every `ParameterGap` with only `parameter_name`/`description`. Every sibling field is
genuinely used (`required` is always its default `True`, correctly, since gaps are only raised for
required parameters). Left in place rather than deleted — a plausible richer clarification-prompt
signal for later, on an otherwise fully-wired class in the cleanest-audited layer of this pass.

### Routing precision fix (first-principles re-audit, 2026-10-25)

`intent_routing.py` previously matched bare substrings, so conversation containing "meeting",
"schedule", "email", "remind" etc. was hijacked into a tool form — including "remind me what
happened with my exam". Rules are now regexes that require a request addressed to Nova (imperative
or "can you …"/"I need you to …"), except `remind me to|about|that|of|at|in|on|tomorrow|tonight|
next|every` and `set|create|add a reminder`, which are inherently requests. The earlier "cleanest
audit — zero bugs" conclusion did not hold; `tests/unit/test_tool_routing_precision.py` pins it.
