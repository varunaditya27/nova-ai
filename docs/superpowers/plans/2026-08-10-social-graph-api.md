# Social-Graph API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose Layer 5's already-persisted social graph (people Nova knows about, their event
timeline, and detected social patterns) as a read-only `GET /people` / `GET /people/{id}` API, plus
a frontend lens.

**Architecture:** Two new FastAPI routes read directly from the existing `PostgresSocialStore`
(no new persistence). New Pydantic response schemas project `SocialNode`/`SocialEvent`/
`SocialPattern` dataclasses into API shapes. Frontend adds a list page, a detail page, a card
component, and a Dock entry — all following the exact patterns already used by `/relationship` and
`/goals`.

**Tech Stack:** FastAPI, Pydantic (`api/schemas.py`), `PostgresSocialStore`
(`infra/db/social_store.py`), Next.js App Router (client components), TanStack Query.

## Global Constraints

- Read-only. No mutation endpoints, no new persistence writes — the spec (§2) is explicit that
  Layer 5 is written only by the State Updater.
- Single-user posture: `state.default_user_id`, same as every other route (no `user_id` param).
- Route tests hit a real `PostgresSocialStore` backed by in-memory SQLite through the real FastAPI
  app — no mocked store, per `tests/unit/api/test_routes_conversation.py`'s established pattern.
- Datetimes serialize as `Optional[str]` ISO format (`.isoformat() if x else None`), matching every
  other `*Out` schema in `api/schemas.py`.

---

### Task 1: Response schemas

**Files:**
- Modify: `api/schemas.py` (append after `RelationshipOut`, ~line 332)

**Interfaces:**
- Produces: `PersonOut`, `SocialEventOut`, `SocialPatternOut`, `PersonDetailOut` — all Pydantic
  `BaseModel` classes consumed by Task 2.

- [ ] **Step 1: Add the schemas**

```python
# ── Social graph (Layer 5) ────────────────────────────────────────────────
class PersonOut(BaseModel):
    person_id: str
    display_name: str
    relationship_type: str
    relationship_valence: float = 0.0
    valence_trend: float = 0.0
    interaction_frequency: str = "unknown"
    is_support_source: bool = False
    active_conflict: bool = False
    mention_count: int = 0
    last_mentioned: Optional[str] = None


class SocialEventOut(BaseModel):
    event_id: str
    event_type: str
    summary: str = ""
    event_valence: float = 0.0
    event_timestamp: Optional[str] = None
    is_resolved: bool = False


class SocialPatternOut(BaseModel):
    pattern_id: str
    pattern_type: str
    plain_language_description: str = ""
    pattern_confidence: float = 0.0
    is_active: bool = True


class PersonDetailOut(PersonOut):
    recent_events: list[SocialEventOut] = []
    active_patterns: list[SocialPatternOut] = []
```

- [ ] **Step 2: Verify the module still imports cleanly**

Run: `.venv/bin/python -c "import api.schemas"`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add api/schemas.py
git commit -m "Add PersonOut/PersonDetailOut schemas for the social-graph API"
```

---

### Task 2: `GET /people` and `GET /people/{person_id}` routes

**Files:**
- Create: `api/routes/people.py`
- Modify: `api/main.py` (import + `app.include_router(people_router)`)

**Interfaces:**
- Consumes: `PersonOut`, `SocialEventOut`, `SocialPatternOut`, `PersonDetailOut` (Task 1);
  `PostgresSocialStore(session_factory)` with `.load_graph(user_id) -> Optional[SocialGraph]`,
  `.recent_events(user_id, limit=200) -> list[SocialEvent]`, `.active_patterns(user_id) ->
  list[SocialPattern]` (`infra/db/social_store.py`, unchanged); `SocialNode`/`SocialEvent`/
  `SocialPattern` field names exactly as in `backend/layer5_relationship/schemas.py` (see Task 3's
  fixture for the full field list).
- Produces: `router` (`APIRouter`), registered at prefix `/people`, importable as
  `from api.routes.people import router as people_router`.

- [ ] **Step 1: Write the route module**

```python
"""People route — read-only view of Layer 5's persisted social graph (single-user).

Reads directly from PostgresSocialStore, the real source of truth. UserWorldModel.relationship_graph
is a narrower derived projection of the same data (api/state.py::make_social_writer) and is not
read here — see docs/superpowers/specs/2026-08-10-social-graph-api-design.md §1.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_state
from api.schemas import PersonDetailOut, PersonOut, SocialEventOut, SocialPatternOut
from infra.db.social_store import PostgresSocialStore

router = APIRouter(prefix="/people", tags=["people"])


def _iso(v):
    return v.isoformat() if v else None


def _person_out(node) -> PersonOut:
    return PersonOut(
        person_id=node.person_id, display_name=node.display_name,
        relationship_type=node.relationship_type,
        relationship_valence=node.relationship_valence, valence_trend=node.valence_trend,
        interaction_frequency=node.interaction_frequency,
        is_support_source=node.is_support_source, active_conflict=node.active_conflict,
        mention_count=node.mention_count, last_mentioned=_iso(node.last_mentioned))


def _event_out(event) -> SocialEventOut:
    return SocialEventOut(
        event_id=event.event_id, event_type=event.event_type, summary=event.summary,
        event_valence=event.event_valence, event_timestamp=_iso(event.event_timestamp),
        is_resolved=event.is_resolved)


def _pattern_out(pattern) -> SocialPatternOut:
    return SocialPatternOut(
        pattern_id=pattern.pattern_id, pattern_type=pattern.pattern_type,
        plain_language_description=pattern.plain_language_description,
        pattern_confidence=pattern.pattern_confidence, is_active=pattern.is_active)


@router.get("", response_model=list[PersonOut])
def list_people(state=Depends(get_state)):
    store = PostgresSocialStore(state.session_factory)
    graph = store.load_graph(state.default_user_id)
    nodes = list(graph.nodes.values()) if graph else []
    nodes.sort(key=lambda n: n.mention_count, reverse=True)
    return [_person_out(n) for n in nodes]


@router.get("/{person_id}", response_model=PersonDetailOut)
def get_person(person_id: str, state=Depends(get_state)):
    store = PostgresSocialStore(state.session_factory)
    graph = store.load_graph(state.default_user_id)
    node = graph.nodes.get(person_id) if graph else None
    if node is None:
        raise HTTPException(status_code=404, detail="person not found")

    events = [e for e in store.recent_events(state.default_user_id) if e.person_id == person_id]
    patterns = [p for p in store.active_patterns(state.default_user_id)
                if person_id in p.person_ids_involved]

    base = _person_out(node)
    return PersonDetailOut(
        **base.model_dump(),
        recent_events=[_event_out(e) for e in events],
        active_patterns=[_pattern_out(p) for p in patterns])
```

- [ ] **Step 2: Register the router in `api/main.py`**

Add the import alongside the other route imports (after `from api.routes.continuity import router
as continuity_router`):

```python
from api.routes.people import router as people_router
```

Add the registration alongside the other `app.include_router(...)` calls (after
`app.include_router(continuity_router)`):

```python
    app.include_router(people_router)
```

- [ ] **Step 3: Verify it imports and mounts cleanly**

Run: `.venv/bin/python -c "from api.main import app; print([r.path for r in app.routes if 'people' in r.path])"`
Expected: `['/people', '/people/{person_id}']`

- [ ] **Step 4: Commit**

```bash
git add api/routes/people.py api/main.py
git commit -m "Add GET /people and GET /people/{id} routes"
```

---

### Task 3: Route tests against a real seeded store

**Files:**
- Create: `tests/unit/api/test_routes_people.py`

**Interfaces:**
- Consumes: `router` from `api.routes.people` (Task 2); `PostgresSocialStore` (unchanged);
  `SocialNode`, `SocialEvent`, `SocialPattern`, `SocialGraph` from
  `backend.layer5_relationship.schemas` (unchanged).

- [ ] **Step 1: Write the test file**

```python
"""People routes: real PostgresSocialStore (SQLite), through the real FastAPI app."""
import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api.dependencies import get_state
from api.routes.people import router as people_router
from backend.layer5_relationship.schemas import SocialEvent, SocialGraph, SocialNode, SocialPattern
from infra.db.engine import init_db, make_session_factory
from infra.db.social_store import PostgresSocialStore

USER = "local-user"


def _client():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(engine)
    factory = make_session_factory(engine)
    state = SimpleNamespace(session_factory=factory, default_user_id=USER)
    app = FastAPI()
    app.include_router(people_router)
    app.dependency_overrides[get_state] = lambda: state
    return TestClient(app, raise_server_exceptions=False), PostgresSocialStore(factory)


def _seed_person(store, **kwargs):
    node = SocialNode(display_name="Priya", relationship_type="close_friend",
                      mention_count=3, **kwargs)
    graph = store.load_graph(USER) or SocialGraph(user_id=USER)
    graph.nodes[node.person_id] = node
    store.save_graph(graph)
    return node


def test_list_people_empty_when_no_graph():
    client, _ = _client()
    assert client.get("/people").json() == []


def test_list_people_sorted_by_mention_count():
    client, store = _client()
    low = _seed_person(store, display_name="Sam", mention_count=1)
    graph = store.load_graph(USER)
    graph.nodes[low.person_id] = low
    high = SocialNode(display_name="Priya", relationship_type="close_friend", mention_count=9)
    graph.nodes[high.person_id] = high
    store.save_graph(graph)

    body = client.get("/people").json()
    assert [p["display_name"] for p in body] == ["Priya", "Sam"]


def test_get_person_not_found_is_404():
    client, _ = _client()
    assert client.get("/people/does-not-exist").status_code == 404


def test_get_person_includes_timeline_and_patterns():
    client, store = _client()
    node = _seed_person(store)

    event = SocialEvent(person_id=node.person_id, event_type="conflict_onset",
                        summary="a disagreement about weekend plans")
    store.save_event(USER, event)

    pattern = SocialPattern(person_ids_involved=[node.person_id],
                            plain_language_description="tension resurfaces around plans")
    store.save_patterns(USER, [pattern])

    body = client.get(f"/people/{node.person_id}").json()
    assert body["display_name"] == "Priya"
    assert len(body["recent_events"]) == 1
    assert body["recent_events"][0]["summary"] == "a disagreement about weekend plans"
    assert len(body["active_patterns"]) == 1
    assert body["active_patterns"][0]["plain_language_description"] == "tension resurfaces around plans"


def test_get_person_excludes_other_peoples_events():
    client, store = _client()
    a = _seed_person(store, display_name="Priya")
    graph = store.load_graph(USER)
    b = SocialNode(display_name="Jordan", relationship_type="friend")
    graph.nodes[b.person_id] = b
    store.save_graph(graph)

    store.save_event(USER, SocialEvent(person_id=b.person_id, summary="about Jordan"))

    body = client.get(f"/people/{a.person_id}").json()
    assert body["recent_events"] == []
```

- [ ] **Step 2: Run the tests, verify they pass**

Run: `.venv/bin/pytest tests/unit/api/test_routes_people.py -v`
Expected: 5 passed.

- [ ] **Step 3: Run the full suite to confirm no regressions**

Run: `.venv/bin/pytest -q`
Expected: all passed, no failures, no new skips.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/api/test_routes_people.py
git commit -m "Add route tests for GET /people and GET /people/{id}"
```

---

### Task 4: `docs/API_REFERENCE.md` entry

**Files:**
- Modify: `docs/API_REFERENCE.md`

**Interfaces:** None (documentation only).

- [ ] **Step 1: Add the route documentation**

Find the section documenting `/relationship` (search for `### \`GET /relationship\``) and add a new
entry immediately after it, matching that entry's format exactly:

```markdown
### `GET /people` → `PersonOut[]`
Every person in Layer 5's social graph, sorted by mention count descending. Read-only projection of
`PostgresSocialStore`.

### `GET /people/{person_id}` → `PersonDetailOut`
One person's full record plus their event timeline (`recent_events`) and any active social patterns
involving them (`active_patterns`). `404` if the id doesn't exist.
```

Also update the summary route-count table at the top of the file: find the row listing
`/relationship` and add a new row for `/people` immediately after it, and increment the total route
count by 2.

- [ ] **Step 2: Commit**

```bash
git add docs/API_REFERENCE.md
git commit -m "Document GET /people and GET /people/{id} in API_REFERENCE.md"
```

---

### Task 5: Frontend types + API client

**Files:**
- Modify: `frontend/lib/api/types.ts` (append after `RelationshipOut`)
- Modify: `frontend/lib/api/client.ts` (append after `getRelationship`, add import)

**Interfaces:**
- Produces: `PersonOut`, `PersonDetailOut` TypeScript types; `getPeople(): Promise<PersonOut[]>`,
  `getPerson(id: string): Promise<PersonDetailOut>` functions consumed by Task 6.

- [ ] **Step 1: Add the types**

In `frontend/lib/api/types.ts`, after the `RelationshipOut` type:

```ts
/** GET /people (Layer 5) — a person in Nova's social graph. */
export type PersonOut = {
  person_id: string;
  display_name: string;
  relationship_type: string;
  relationship_valence: number;
  valence_trend: number;
  interaction_frequency: string;
  is_support_source: boolean;
  active_conflict: boolean;
  mention_count: number;
  last_mentioned: string | null;
};

export type SocialEvent = {
  event_id: string;
  event_type: string;
  summary: string;
  event_valence: number;
  event_timestamp: string | null;
  is_resolved: boolean;
};

export type SocialPattern = {
  pattern_id: string;
  pattern_type: string;
  plain_language_description: string;
  pattern_confidence: number;
  is_active: boolean;
};

/** GET /people/{id} — one person's full record + timeline. */
export type PersonDetailOut = PersonOut & {
  recent_events: SocialEvent[];
  active_patterns: SocialPattern[];
};
```

- [ ] **Step 2: Add the client functions**

In `frontend/lib/api/client.ts`, add `PersonDetailOut` and `PersonOut` to the existing `import { ...
} from "./types"` block (alphabetically, matching the existing order), then add after
`getRelationship`:

```ts
export function getPeople(): Promise<PersonOut[]> {
  return requestJson<PersonOut[]>("/people");
}

export function getPerson(personId: string): Promise<PersonDetailOut> {
  return requestJson<PersonDetailOut>(`/people/${encodeURIComponent(personId)}`);
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api/types.ts frontend/lib/api/client.ts
git commit -m "Add People API types and client functions"
```

---

### Task 6: `usePeople` hook

**Files:**
- Create: `frontend/lib/hooks/usePeople.ts`

**Interfaces:**
- Consumes: `getPeople`, `getPerson` (Task 5).
- Produces: `usePeople()`, `usePerson(id: string)` — both `useQuery` results, consumed by Task 7.

- [ ] **Step 1: Write the hook**

```ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { getPeople, getPerson } from "@/lib/api/client";

export function usePeople() {
  return useQuery({ queryKey: ["people"], queryFn: getPeople });
}

export function usePerson(personId: string) {
  return useQuery({
    queryKey: ["people", personId],
    queryFn: () => getPerson(personId),
    enabled: Boolean(personId),
  });
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/hooks/usePeople.ts
git commit -m "Add usePeople/usePerson hooks"
```

---

### Task 7: `PersonCard` component + `/people` list page

**Files:**
- Create: `frontend/components/people/PersonCard.tsx`
- Create: `frontend/app/people/page.tsx`

**Interfaces:**
- Consumes: `PersonOut` (Task 5), `usePeople` (Task 6), `Surface` (`components/primitives/Surface`),
  `Meter` (`components/primitives/Meter`), `PageShell` (`components/primitives/PageShell`) —
  unchanged.
- Produces: `PersonCard` component, `/people` route, consumed visually by the Dock entry in Task 9.

- [ ] **Step 1: Write `PersonCard`**

```tsx
"use client";

import Link from "next/link";
import { Surface } from "@/components/primitives/Surface";
import { Meter } from "@/components/primitives/Meter";
import type { PersonOut } from "@/lib/api/types";

/** A person Nova knows about — relationship type, valence, and whether there's active tension. */
export function PersonCard({ person }: { person: PersonOut }) {
  return (
    <Link href={`/people/${person.person_id}`}>
      <Surface className="p-5 transition-colors hover:bg-raised">
        <div className="flex items-baseline justify-between gap-3">
          <p className="font-display text-lg text-ink">{person.display_name}</p>
          <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
            {person.relationship_type.replace(/_/g, " ")}
          </span>
        </div>
        <Meter
          value={(person.relationship_valence + 1) / 2}
          brass={person.is_support_source}
          className="mt-3"
        />
        <div className="mt-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
          <span>{person.mention_count} mention{person.mention_count === 1 ? "" : "s"}</span>
          {person.active_conflict && <span className="text-brass">active tension</span>}
        </div>
      </Surface>
    </Link>
  );
}
```

- [ ] **Step 2: Write the list page**

```tsx
"use client";

import { PageShell } from "@/components/primitives/PageShell";
import { PersonCard } from "@/components/people/PersonCard";
import { usePeople } from "@/lib/hooks/usePeople";

/** People — everyone Nova has learned about from what you've said, never inferred. */
export default function People() {
  const { data, isLoading } = usePeople();

  return (
    <PageShell
      title="People"
      description="Everyone Nova has learned about from what you've told it — nothing guessed."
    >
      {isLoading && <div className="h-40 rounded-md bg-hairline/30" />}
      {data && data.length === 0 && (
        <p className="text-ink-soft">No one yet — mention someone and Nova will remember them.</p>
      )}
      {data && data.length > 0 && (
        <div className="flex flex-col gap-3">
          {data.map((p) => (
            <PersonCard key={p.person_id} person={p} />
          ))}
        </div>
      )}
    </PageShell>
  );
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/people/PersonCard.tsx frontend/app/people/page.tsx
git commit -m "Add PersonCard and /people list page"
```

---

### Task 8: `/people/[id]` detail page

**Files:**
- Create: `frontend/app/people/[id]/page.tsx`

**Interfaces:**
- Consumes: `usePerson` (Task 6), `PageShell`, `Surface`, `Meter` (unchanged).

- [ ] **Step 1: Write the detail page**

```tsx
"use client";

import { useParams } from "next/navigation";
import { PageShell } from "@/components/primitives/PageShell";
import { Surface } from "@/components/primitives/Surface";
import { Meter } from "@/components/primitives/Meter";
import { usePerson } from "@/lib/hooks/usePeople";

export default function PersonDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = usePerson(id);

  return (
    <PageShell title={data?.display_name ?? "Person"} description={data?.relationship_type.replace(/_/g, " ")}>
      {isLoading && <div className="h-40 rounded-md bg-hairline/30" />}
      {data && (
        <div className="flex flex-col gap-8">
          <Meter
            value={(data.relationship_valence + 1) / 2}
            brass={data.is_support_source}
            leftLabel="strained"
            rightLabel="warm"
          />

          {data.active_patterns.length > 0 && (
            <div>
              <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                patterns
              </p>
              <div className="flex flex-col gap-2">
                {data.active_patterns.map((p) => (
                  <Surface key={p.pattern_id} className="p-4">
                    <p className="text-[15px] text-ink">{p.plain_language_description}</p>
                  </Surface>
                ))}
              </div>
            </div>
          )}

          <div>
            <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-ink-faint">
              timeline · {data.recent_events.length}
            </p>
            {data.recent_events.length === 0 && (
              <p className="text-ink-soft">Nothing recorded yet.</p>
            )}
            <div className="flex flex-col gap-2">
              {data.recent_events.map((e) => (
                <Surface key={e.event_id} className="p-4">
                  <p className="text-[15px] text-ink">{e.summary}</p>
                  <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
                    {e.event_type.replace(/_/g, " ")}
                    {e.is_resolved ? " · resolved" : ""}
                  </p>
                </Surface>
              ))}
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/people/[id]/page.tsx"
git commit -m "Add /people/[id] detail page"
```

---

### Task 9: Wire into the Dock's Lenses popover

**Files:**
- Modify: `frontend/components/primitives/Dock.tsx`

**Interfaces:** None new — inserts into the existing `LENSES` array.

- [ ] **Step 1: Add the entry**

In the `LENSES` array (after the `{ href: "/relationship", label: "Relationship", enabled: true
},` line), add:

```ts
  { href: "/people", label: "People", enabled: true },
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/primitives/Dock.tsx
git commit -m "Add People to the Dock's Lenses popover"
```

---

### Task 10: Live verification

**Files:** None (verification only).

- [ ] **Step 1: Run the full backend suite**

Run: `.venv/bin/pytest -q`
Expected: all passed.

- [ ] **Step 2: Run frontend lint + typecheck + unit tests**

Run: `cd frontend && ./node_modules/.bin/eslint . && ./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/vitest run`
Expected: all clean, all passed.

- [ ] **Step 3: Live walk with real backend running**

With Postgres/Chroma up and the API server running against them (see `scripts/run_local.sh`), drive
a real conversation that mentions a person by name (e.g. "my friend Priya and I had a disagreement
about weekend plans"), confirm Layer 5 persists them (already-existing, unchanged behavior), then:

1. `curl -s http://127.0.0.1:8000/people | python3 -m json.tool` — confirm the person appears.
2. Start the frontend dev server (`cd frontend && npm run dev`), navigate to `/people`, confirm the
   card renders with real data, click into `/people/{id}`, confirm the detail page renders the
   timeline.

- [ ] **Step 4: Update `frontend/DEFERRED_WORK.md`**

Remove item #3 ("People / social graph") entirely, since it's now built — it's no longer deferred.
Also update `docs/POLISH_BACKLOG.md`'s Layer 5 section: find the line about no API exposing the
social graph and mark it `[done, 2026-08-10]` with a one-line pointer to this feature.

- [ ] **Step 5: Commit**

```bash
git add frontend/DEFERRED_WORK.md docs/POLISH_BACKLOG.md
git commit -m "Mark social-graph API deferred-work item done"
```
