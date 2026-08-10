# Social-Graph API — Design Spec

**Date:** 2026-08-10
**Status:** Approved, implementing
**Scope:** Expose Layer 5's already-persisted `SocialGraph` (people Nova knows about) as a
read-only API + frontend lens. Closes `frontend/DEFERRED_WORK.md` #3.

---

## 1. Motivation

Layer 5 (`backend/layer5_relationship/`) builds and persists a full social model — named people,
relationship type/valence/conflict history/support role (`SocialNode`), a timeline of detected
interpersonal events (`SocialEvent`), and recurring social dynamics (`SocialPattern`) — via
`PostgresSocialStore`. Nothing reads any of it back. This closes that gap with a read-only surface,
matching the shape already sketched in `DEFERRED_WORK.md` #3 ("`GET /people`, `GET /people/{id}`
(summary, timeline, shared mentions)").

`UserWorldModel.relationship_graph` (`backend/layer2_memory/schemas.py::RelationshipGraph`) is
**not** a second source to reconcile — `api/state.py`'s `make_social_writer` projects Layer 5's
`SocialNode`s onto it as a narrower, prompt-injection-only slice (fewer fields: no conflict count,
no support role, no interaction frequency). This API reads directly from `PostgresSocialStore`,
the real source of truth, and ignores the UWM projection entirely.

## 2. Design decisions

| Decision | Choice |
|---|---|
| Mutation | None. Read-only, matching Layer 5's "user-stated only, written only by the State Updater" invariant — same posture as `GET /memory/audit`. |
| List sort | `mention_count` descending (most-mentioned people first). |
| Detail = node + timeline | Node fields as-is, plus `recent_events` (that person's `SocialEvent`s, newest first, from `PostgresSocialStore.recent_events`) and `active_patterns` (`SocialPattern`s where the person is in `person_ids_involved`). |
| Not-found | 404 on an unknown `person_id`, matching `GET /memory/{id}`'s existing convention. |
| User scoping | `state.default_user_id`, same single-user posture as every other route. |

## 3. Components

### 3.1 `api/schemas.py` additions
- `PersonOut`: `person_id, display_name, relationship_type, relationship_valence, valence_trend, interaction_frequency, is_support_source, active_conflict, mention_count, last_mentioned`.
- `SocialEventOut`: `event_id, event_type, summary, event_valence, event_timestamp, is_resolved`.
- `SocialPatternOut`: `pattern_id, pattern_type, plain_language_description, pattern_confidence, is_active`.
- `PersonDetailOut`: `PersonOut` fields + `recent_events: list[SocialEventOut]` + `active_patterns: list[SocialPatternOut]`.

### 3.2 `api/routes/people.py` (new)
- `GET /people` → `list[PersonOut]`, all nodes from `PostgresSocialStore.load_graph(user_id)`, sorted by `mention_count` desc.
- `GET /people/{person_id}` → `PersonDetailOut`, or 404. Events filtered from `recent_events(user_id)` by `person_id`; patterns filtered from `active_patterns(user_id)` by membership in `person_ids_involved`.

Registered in `api/main.py` alongside the other lens routers.

### 3.3 Frontend
- `lib/api/types.ts` + `lib/api/client.ts`: `PersonOut`/`PersonDetailOut` types, `getPeople()`/`getPerson(id)`.
- `lib/hooks/usePeople.ts`: `usePeople()` / `usePerson(id)` (`useQuery`, matching `useVault.ts`'s pattern).
- `components/people/PersonCard.tsx`: summary card (name, relationship type, valence meter), styled like `GoalCard`.
- `app/people/page.tsx`: list view, `PageShell`.
- `app/people/[id]/page.tsx`: detail view — node facts, event timeline, active patterns.
- Added to `components/primitives/Dock.tsx`'s `LENSES` array as `{ href: "/people", label: "People", enabled: true }`.

## 4. Testing
- `tests/unit/api/test_routes_people.py`: seed a `PostgresSocialStore` with real nodes/events/patterns (SQLite), hit both routes through the real FastAPI app, assert shape and 404 behavior — no mocked store, per this repo's route-testing convention.
- Frontend: no new vitest coverage needed (thin data-fetching hooks + presentational components, consistent with the rest of the lens pages); verified live via a real browser walk against seeded data before calling it done.

## 5. Success criteria
1. `GET /people` returns real people Nova has learned about from real conversation history.
2. `GET /people/{id}` returns that person's timeline and any patterns involving them.
3. `/people` is reachable from the Dock and renders real data end-to-end.

## 6. Non-goals
Editing/merging people (no correction UI, unlike Layer 12's memory correction — Layer 5 has no
correction interface to wire to). Person-to-person edges / the "Universe" life-graph view
(`DEFERRED_WORK.md` #4 — separate, larger, still deferred). `SocialEdge` persistence (still
correctly unwired per `docs/layer-5-architecture.md`'s Live Wiring Status — no real SC-1 function
builds edges yet, a deliberate prior decision, not touched here).
