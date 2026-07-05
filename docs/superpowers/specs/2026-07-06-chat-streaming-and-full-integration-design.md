# Chat Streaming + Full 13-Layer Integration — Design

**Status:** Implemented
**Date:** 2026-07-06
**Branch:** `chat-streaming-and-integration`

## Goal

Two related deliverables that make the backend API and the 13-layer pipeline genuinely
end-to-end:

1. **Close the last two orchestrator integration gaps** so every `/chat` turn exercises all
   13 layers: wire Layer 11 SC-1 (`guardrails`) and Layer 13 (`cold_start`), the only
   `PipelineSteps` hooks still left as `None` in `api/assembly.py`.
2. **Add `POST /chat/stream`** — Server-Sent Events (SSE) streaming of the response as paced
   token events.

Auth / multi-user is explicitly out of scope for this increment.

## Part A — Complete the pipeline integration

### A1. SC-1 Ethical Guardrails (`guardrails` hook)

Currently unwired: the live `/chat` path never runs post-generation ethical guardrails — a real
safety gap. Layer 11 exposes `run_all_checks(proposed_response, session_context, …) ->
EthicalGuardrailResult{passed, final_response, violations, replacement_triggered}`. The
orchestrator expects `{approved, replacement, flags}` and only swaps text when `not approved`.

**Adapter (in `api/assembly.py`):** map faithfully so *any* SC-1 change is applied, not just hard
blocks:

```python
result = run_all_checks(response, _guardrail_ctx(ctx))
changed = bool(result.final_response) and result.final_response != response
return _GuardrailResult(
    approved=not changed,                       # swap whenever SC-1 altered the text
    replacement=result.final_response,
    flags=[v.check_name for v in result.violations])
```

`_guardrail_ctx(ctx)` is a minimal `SimpleNamespace(session_id=ctx.session_id,
has_real_deadline=False, vulnerability_score=0.0)`; `longitudinal_record` is left `None`
(single-user, no longitudinal record threaded through the live path yet — the sycophancy/
validation checks are no-ops without it, which is correct: they need history we do not yet
persist per-turn). This wires the two **response-content** checks (manipulation, artificial
urgency, vulnerability-exploit, anthropomorphism boundary) that operate purely on the text.

### A2. Cold-start overlay (`cold_start` hook)

Was blocked on onboarding persistence, which now exists (`PostgresOnboardingStore`, PR #24).

`ColdStartEngine.on_message` needs a rich `session_context` (recent_history, emotional_intensity,
feature_triggers, elicitation counters) that the orchestrator's `TurnContext` does not carry and
that we do not persist. So the wiring is **persisted-state-driven**, not machinery-driven: the
hook reads `PostgresOnboardingStore.state()` and

- returns `None` once `cold_start_active` is `False` (graduated → no overlay), and
- while cold-starting returns a lightweight directives object carrying exactly what the
  orchestrator consumes (`getattr` on `proactivity_mode`, `personality_drift_gate`,
  `pending_elicitation`): `observe_only` proactivity and a `0.30` drift gate.

The graduation counter is already advanced post-turn by `make_onboarding_writer`, so the overlay
self-terminates. **Deferred (documented follow-up):** running the full elicitation / feature-pacing
machinery, which needs a persisted session_context this increment does not build.

Built in `api/state.py` (needs Postgres) and injected into `build_pipeline_steps(..., cold_start=…)`;
`guardrails` is built inside `assembly.py` (pure backend, no infra).

## Part B — SSE streaming (`POST /chat/stream`)

### Why paced delivery, not token-from-LLM

Nova's invariant: **SC-1 runs post-generation, before Layer 9 delivers.** Raw LLM tokens must not
reach the user before the ethical check. Layer 9 already ships the correct mechanism —
`StreamTypingOverlay` takes the *finished, approved* response and emits mode-/circadian-paced
token+pause events ("the full response is available; the UI renders tokens with these delays").
So `/chat/stream` runs the **full turn** (crisis veto + SC-1 + all post-turn writes exactly as
`/chat`), then replays the delivered text as paced SSE events. This is the architecturally correct
mechanism, not a compromise.

### Event protocol

`text/event-stream`, three event types:

```
event: meta
data: {"session_id","conversation_mode","cognitive_system","crisis_active","refined","confabulation_guard"}

event: token
data: {"token": "...", "delay_ms": <int>}      # one per token, in order

event: done
data: {"crisis_active","refined","conversation_mode","cognitive_system","session_id"}
```

Concatenating all `token` values reconstructs the delivered response exactly.

### Components

- `api/streaming.py`:
  - `_MODE_TO_TYPING` maps L3 conversation modes → overlay modes (`casual`→`casual_chat`,
    `emotional_support`→`emotional_support`, `crisis`→`crisis_support`,
    `technical_discussion`→`technical`, `goal_planning`/`life_review`→`deep_reasoning`,
    `social_coaching`→`emotional_support`, `celebration`→`celebration`; default `casual_chat`).
  - `_circadian_band(now)` — hour→band for the overlay's delay modulation.
  - `_tokenize(text)` — `re.findall(r"\S+\s*|\s+", text)` (whitespace-preserving; concatenation is lossless).
  - `stream_turn(orchestrator, overlay, user_id, message, session_id, now=None) -> Iterator[str]`:
    runs `orchestrator.run_turn(...)` once, yields the `meta` SSE frame, then for each token yields
    a `token` frame whose `delay_ms` comes from `overlay.emit_token(...)` (summing any sentence
    pause into the token's delay), then the `done` frame. Deterministic `rng` injectable for tests.
- `api/routes/chat.py`: `POST /chat/stream` → `StreamingResponse(stream_turn(...),
  media_type="text/event-stream")`. Sync generator ⇒ Starlette iterates it in the threadpool, so
  the assembly async→sync bridge stays safe (no running loop in that thread), same as `/chat`.

## Testing

- `test_guardrails_adapter` — a manipulation-pattern response is blocked+replaced; a clean response
  passes unchanged.
- `test_cold_start_adapter` — active state → directives (observe_only, 0.30); graduated state → None.
- `test_streaming` — `stream_turn` over a fake orchestrator: exactly one `meta`, N `token`, one
  `done`; tokens concatenate to the response; all `delay_ms` ≥ overlay floor.
- `test_chat_stream_route` — `TestClient` `POST /chat/stream`, parse SSE, assert reconstructed text
  and terminal `done`.
- Offline invariant holds: all new tests `pytest.importorskip` their heavy deps; the pure pipeline
  suite stays green on bare `/usr/bin/python3.11`.

## Non-goals

Auth/multi-user, WebSocket transport (SSE chosen; WS is the future bidirectional upgrade),
token-from-LLM streaming (violates the SC-1-before-delivery invariant), the full Layer-13
elicitation machinery, Layer-8 tool execution, Layer-12 sync/deletion.
