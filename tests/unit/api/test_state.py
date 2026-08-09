import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pydantic")

from datetime import datetime, timedelta, timezone

from infra.db import make_engine, make_session_factory, init_db, session_scope
import infra.db.models as models
from infra.db.memory_store import PostgresMemoryStore
from infra.db.audit_trail import PostgresAuditTrail
from backend.layer2_memory.schemas import (
    ConversationTurn, EmotionVector, EpisodicMemory, ScoredMemory, ShortTermMemoryBuffer,
)
from api.state import build_app_state, make_state_update_writer, make_cold_start_provider
from infra.stm_store import InProcessSTMStore


class FakeLLM:
    def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
        return "hi there"
    def stream(self, prompt, **k):
        yield "hi there"
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def _sqlite_state():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    return build_app_state(config={"system": {"default_user_id": "local-user"},
                                   "llm": {}, "memory": {}},
                           llm_clients=clients, engine=engine, vector_store=object())


class Ctx:
    user_id = "local-user"
    session_id = "s1"
    message = "hey there"
    now = datetime.now(timezone.utc)
    response_text = "loves hiking"
    emotion_intent = None
    recalled_memories = []
    client_metadata = {}


def test_build_app_state_runs_a_turn():
    state = _sqlite_state()
    out = state.orchestrator.run_turn(state.default_user_id, "hey")
    assert out.response_text.strip()


def test_build_app_state_seeds_identity_beliefs_once_idempotently():
    """Closes 'Identity Memory is never seeded': build_app_state seeds Nova's self-model on boot
    if the table is empty, and never re-seeds (duplicates) on a later boot against the same DB."""
    from infra.db.memory_store import PostgresMemoryStore

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    clients = {"system1": FakeLLM(), "system2": FakeLLM(), "embed": FakeLLM()}
    config = {"system": {"default_user_id": "local-user"}, "llm": {}, "memory": {}}

    state1 = build_app_state(config=config, llm_clients=clients, engine=engine, vector_store=object())
    seeded = PostgresMemoryStore(state1.session_factory).identity_beliefs()
    assert len(seeded) > 0
    assert any(b.is_immutable for b in seeded)

    build_app_state(config=config, llm_clients=clients, engine=engine, vector_store=object())
    assert len(PostgresMemoryStore(state1.session_factory).identity_beliefs()) == len(seeded)


def test_writer_updates_session_and_audit_without_creating_an_episode_from_one_ordinary_turn():
    """One ordinary turn is added to STM but not evicted (buffer holds 100), so no episode is
    created — matches the real promotion-only design (docs/layer-2-architecture.md §3.3), not
    the old every-turn-truncation stub. Session bookkeeping and the audit chain still run."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                             stm_store=InProcessSTMStore())(Ctx())
    assert store.active_episodic("local-user") == []
    with session_scope(factory) as s:
        row = s.query(models.Session).filter_by(session_key="s1").one()
        assert row.turn_count == 1
        # last_delivered_at (Layer 1 SC-2's real latency-signal source) stamped for real, not
        # left null -- the next turn's perceive() reads this back via
        # make_session_last_delivered_provider.
        assert row.last_delivered_at is not None
    assert PostgresAuditTrail(factory, "local-user").verify() is True


class _EmotionIntent:
    def __init__(self, valence, arousal):
        self.emotion_vector = EmotionVector(valence=valence, arousal=arousal)


def test_writer_promotes_high_arousal_turn_on_arrival_to_llm_summarized_episode():
    """A turn with arousal above the promotion threshold must become a real episodic memory
    on arrival — summarized by the injected LLM, not raw-truncated."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)

    class C(Ctx):
        message = "I just found out I got the job!!"
        response_text = "That's amazing news!"
        emotion_intent = _EmotionIntent(valence=0.8, arousal=0.9)

    class SummarizingLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return '{"summary": "User got a new job.", "entities": ["employer"]}'

    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1, stm_store=InProcessSTMStore(),
                             summarizer_llm=SummarizingLLM())(C())

    episodes = store.active_episodic("local-user")
    assert any(m.summary == "User got a new job." for m in episodes)
    promoted = next(m for m in episodes if m.summary == "User got a new job.")
    assert promoted.emotion_vector.arousal == pytest.approx(0.9)
    assert promoted.entity_refs == ["employer"]


def test_writer_promotes_a_high_arousal_turn_on_arrival_without_needing_stm_eviction():
    """Real sessions (a handful of turns) essentially never fill the 100-turn/30,000-char STM
    window, so eviction-only promotion would mean significant turns are rarely, if ever, actually
    persisted. A high-arousal turn must be promoted immediately, not only when later evicted."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)

    class C(Ctx):
        message = "I just found out my grandmother passed away"
        response_text = "I'm so sorry for your loss."
        emotion_intent = _EmotionIntent(valence=-0.8, arousal=0.9)

    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                             stm_store=InProcessSTMStore())(C())

    episodes = store.active_episodic("local-user")
    assert len(episodes) == 1
    assert episodes[0].emotion_vector.arousal == pytest.approx(0.9)


def test_writer_never_promotes_a_life_event_keyword_in_novas_own_reply():
    """Promotion is decided only at arrival, and only for user turns -- an assistant turn already
    in STM (even one matching a life-event keyword like "congratulations on the new job") must
    never be promoted just because it's later evicted. Force eviction with a tiny buffer to prove
    eviction alone never triggers promotion, rather than passing trivially because nothing evicted."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)

    stm_store = InProcessSTMStore()
    buf = ShortTermMemoryBuffer(session_id="s1", user_id="local-user", max_turns=1, char_limit=10_000)
    old_reply = ConversationTurn(role="assistant", content="Congratulations on the new job!",
                                 timestamp=datetime.now(timezone.utc))
    buf.turns.append(old_reply)
    buf.total_chars += len(old_reply.content)
    stm_store.save("s1", buf)

    class C(Ctx):
        message = "guess what"
        response_text = "tell me!"

    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1, stm_store=stm_store)(C())
    assert store.active_episodic("local-user") == []


def test_writer_seeds_a_narrative_chain_from_a_promoted_episode():
    """A promoted episode with no existing chain to attach to seeds a new one (§10.3)."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)

    class C(Ctx):
        message = "I just got the job!!"
        response_text = "That's wonderful news!"

    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                             stm_store=InProcessSTMStore())(C())

    chains = store.active_narrative_chains("local-user")
    assert len(chains) == 1
    assert len(chains[0].episodes) == 1


def test_writer_cannot_link_two_episodes_without_entity_overlap_even_at_perfect_similarity():
    """detect_narrative_links's formula (§10.3) is `0.6*semantic + 0.4*entity_overlap` against a
    0.65 threshold. Without a summarizer LLM, `entity_refs` falls back to `[]`, so entity_overlap
    is always 0 -- capping the achievable score at 0.6*semantic <= 0.6, which can never cross 0.65
    even at perfect (1.0) semantic similarity (as with this FakeLLM stub, which embeds every
    summary identically). Two clearly-related episodes therefore each seed their own singleton
    chain in this configuration -- documents the real ceiling when entity extraction is
    unavailable, rather than asserting linking that cannot happen without it."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    write = make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                                     stm_store=InProcessSTMStore())

    class C1(Ctx):
        message = "I just got the job!!"
        response_text = "That's wonderful news!"

    class C2(Ctx):
        message = "guess what, I got promoted at work"
        response_text = "Congratulations!"

    write(C1())
    write(C2())

    chains = store.active_narrative_chains("local-user")
    assert len(chains) == 2
    assert all(len(c.episodes) == 1 for c in chains)


def test_writer_links_two_episodes_that_share_an_extracted_entity():
    """With a summarizer LLM that extracts a shared entity, entity_overlap=1.0 pushes link_score
    to 0.6*1.0 + 0.4*1.0 = 1.0 > 0.65 (embeddings are identical under the FakeLLM stub), so the
    second promoted episode continues the first's chain instead of seeding a new one."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)

    class EntityLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return '{"summary": "About the new job.", "entities": ["Acme Corp"]}'

    write = make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                                     stm_store=InProcessSTMStore(), summarizer_llm=EntityLLM())

    class C1(Ctx):
        message = "I just got the job at Acme Corp!!"
        response_text = "That's wonderful news!"

    class C2(Ctx):
        message = "guess what, I got promoted at Acme Corp"
        response_text = "Congratulations!"

    write(C1())
    write(C2())

    chains = store.active_narrative_chains("local-user")
    assert len(chains) == 1
    assert len(chains[0].episodes) == 2


def test_writer_creates_and_merges_the_user_world_model_from_extracted_signals():
    """Closes 'UWM is never created for any real user': the post-turn writer now extracts
    profile/people/situation signals via the injected LLM and merges them into a real,
    persisted UserWorldModel -- on the very first turn, with no pre-existing row.

    NOTE on "people": this test runs with no social_writer_fn, so it exercises the fallback
    path only -- _extract_uwm_signals no longer asks the LLM about people at all (see its
    docstring), but a raw LLM response containing a "people" key is still merged verbatim when
    nothing from Layer 5 overrides it (degrade-gracefully, not silently drop real signal). In
    live production social_writer_fn is always wired (see build_app_state), so the people list
    actually reaching the UWM comes from Layer 5's real SocialGraph resolution instead -- see
    test_social_writer_creates_a_node_and_projects_it_onto_the_uwm_through_the_real_stores."""
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)

    class UWMLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return ('{"profile": {"preferred_name": "Sam", "field_of_study_or_work": "nursing"}, '
                    '"people": [{"name": "Maya", "relationship_tier": "friend"}]}')

    class C(Ctx):
        message = "I'm Sam, I study nursing. My friend Maya has been so supportive."
        response_text = "That's great to hear!"

    assert store.load_uwm("local-user") is None
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                             summarizer_llm=UWMLLM())(C())

    uwm = store.load_uwm("local-user")
    assert uwm is not None
    assert uwm.profile.preferred_name == "Sam"
    assert uwm.profile.field_of_study_or_work == "nursing"
    assert [p.name for p in uwm.relationship_graph.people] == ["Maya"]


def test_social_writer_creates_a_node_and_projects_it_onto_the_uwm_through_the_real_stores():
    """Layer 5 was correct, tested, and had zero production callers -- no persistence, no
    per-turn extraction, no orchestrator hook. This closes the persistence + extraction half:
    a named third party is resolved into a real SocialGraph node (SC-1's real resolve_entity/
    create_node, not reimplemented logic), persisted, and projected onto
    UWM.relationship_graph.people -- proving Layer 5 is now the one place person mentions are
    resolved (not a second, independent UWM extraction call)."""
    from api.state import make_social_writer
    from infra.db.social_store import PostgresSocialStore

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    social_store = PostgresSocialStore(factory)

    class MentionLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "named third party" in prompt:
                return '{"mentions": [{"name": "Maya", "context": "my sister Maya"}]}'
            return '{}'   # UWM's own profile/situations/stressors call: nothing to report

    class C(Ctx):
        message = "My sister Maya called me today and it was really nice to catch up."
        response_text = "That sounds lovely."

    llm = MentionLLM()
    write = make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                                     summarizer_llm=llm,
                                     social_writer_fn=make_social_writer(factory, llm))
    write(C())

    graph = social_store.load_graph("local-user")
    assert graph is not None
    assert len(graph.nodes) == 1
    node = next(iter(graph.nodes.values()))
    assert node.display_name == "Maya"
    assert node.relationship_type == "family_immediate"   # inferred from "sister" in context
    assert node.mention_count == 1

    uwm = store.load_uwm("local-user")
    people = uwm.relationship_graph.people
    assert [p.name for p in people] == ["Maya"]
    assert people[0].relationship_tier == "family"   # projected via _RELATIONSHIP_TIER_MAP


def test_social_writer_increments_mention_count_on_a_repeat_mention_instead_of_duplicating():
    """A second turn naming the same person must resolve to the SAME node (SC-1's
    resolve_entity alias matching), not create a duplicate -- proves the writer round-trips
    through the persisted graph correctly across turns, not just within one."""
    from api.state import make_social_writer
    from infra.db.social_store import PostgresSocialStore

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    social_store = PostgresSocialStore(factory)

    class MentionLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "named third party" in prompt:
                return '{"mentions": [{"name": "Maya", "context": "my friend Maya"}]}'
            return '{}'

    llm = MentionLLM()
    social_writer = make_social_writer(factory, llm)

    class C1(Ctx):
        message = "My friend Maya and I hung out."
        response_text = "Nice!"

    class C2(Ctx):
        message = "Maya texted me again today."
        response_text = "That's great."

    write = make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                                     summarizer_llm=llm, social_writer_fn=social_writer)
    write(C1())
    write(C2())

    graph = social_store.load_graph("local-user")
    assert len(graph.nodes) == 1
    node = next(iter(graph.nodes.values()))
    assert node.mention_count == 2


def test_social_writer_does_not_merge_two_different_people_who_share_a_relationship_type():
    """resolve_entity's relationship-type-from-context match sits at exactly 0.70 confidence --
    a *tentative* match (is_tentative_match's [0.65, 0.80) range), not a confirmed one. Without
    treating a tentative match as a new entity, a second friend named in a later turn would
    silently resolve onto the first friend's node (same relationship_type = "friend" match)."""
    from api.state import make_social_writer
    from infra.db.social_store import PostgresSocialStore

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    social_store = PostgresSocialStore(factory)

    class MentionLLM(FakeLLM):
        def __init__(self, name):
            self._name = name
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "named third party" in prompt:
                return f'{{"mentions": [{{"name": "{self._name}", "context": "my friend {self._name}"}}]}}'
            return '{}'
        def embed(self, texts):
            return [[0.1, 0.2, 0.3] for _ in texts]

    social_writer_maya = make_social_writer(factory, MentionLLM("Maya"))
    social_writer_alex = make_social_writer(factory, MentionLLM("Alex"))

    class C1(Ctx):
        message = "My friend Maya and I hung out."
        response_text = "Nice!"

    class C2(Ctx):
        message = "My friend Alex came over too."
        response_text = "Sounds fun."

    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                             summarizer_llm=MentionLLM("Maya"),
                             social_writer_fn=social_writer_maya)(C1())
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                             summarizer_llm=MentionLLM("Alex"),
                             social_writer_fn=social_writer_alex)(C2())

    graph = social_store.load_graph("local-user")
    assert len(graph.nodes) == 2
    assert {n.display_name for n in graph.nodes.values()} == {"Maya", "Alex"}


def test_social_writer_does_not_double_count_the_same_person_mentioned_twice_in_one_turn():
    """A turn naming the same person twice ("Maya called, then Maya texted later") must count as
    one mention-worth of signal, not two -- and must still be treated as a single-person turn so
    event attribution (which only fires for exactly one resolved person) isn't skipped."""
    from api.state import make_social_writer
    from infra.db.social_store import PostgresSocialStore

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    social_store = PostgresSocialStore(factory)

    class MentionLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "named third party" in prompt:
                return ('{"mentions": [{"name": "Maya", "context": "my friend Maya called"}, '
                        '{"name": "Maya", "context": "Maya texted later"}]}')
            return '{}'

    llm = MentionLLM()
    write = make_state_update_writer(store, FakeLLM(), factory, threshold=0.1,
                                     summarizer_llm=llm,
                                     social_writer_fn=make_social_writer(factory, llm))

    class C(Ctx):
        message = "My friend Maya called, then Maya texted later."
        response_text = "Sounds like a full day!"

    write(C())

    graph = social_store.load_graph("local-user")
    assert len(graph.nodes) == 1
    node = next(iter(graph.nodes.values()))
    assert node.mention_count == 1   # one turn, not two, even though the name appeared twice

    uwm = store.load_uwm("local-user")
    assert len(uwm.relationship_graph.people) == 1   # UWM projection also not double-counted


def test_identity_writer_accumulates_evidence_and_updates_a_belief_through_the_real_store():
    """Closes 'Identity Memory is never seeded or updated' end to end: seeded beliefs, a real
    contradiction-detection LLM call per turn, and a real rewrite once accumulated evidence
    crosses the centrality-scaled threshold -- against the real PostgresMemoryStore, not a mock."""
    from api.state import make_identity_writer
    from backend.layer2_memory.identity_seed import default_identity_beliefs

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    for belief in default_identity_beliefs():
        store.save_identity(belief)
    target = next(b for b in store.identity_beliefs()
                  if b.category.value == "personality_trait" and not b.is_immutable)

    class ContradictingLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "revised version" in prompt:
                return "Nova adapts her personality traits based on what the user tells her."
            return (f'[{{"belief_id": "{target.belief_id}", "contradiction_score": 0.9, '
                    f'"reason": "user directly disagreed"}}]')

    write = make_identity_writer(factory, ContradictingLLM())

    class C(Ctx):
        message = "that's not true about you at all"

    write(C())

    updated = next(b for b in store.identity_beliefs() if b.belief_id == target.belief_id)
    assert updated.statement != target.statement
    assert "[revised]" not in updated.statement   # never the offline placeholder in production
    assert updated.statement == "Nova adapts her personality traits based on what the user tells her."
    assert len(updated.update_history) == 1


def test_identity_writer_leaves_belief_unchanged_when_rewrite_generation_fails():
    """If the LLM's rewrite call fails or returns nothing, apply_identity_update must treat that
    as 'couldn't rewrite this turn' -- never persist a placeholder like '[revised] <statement>'.
    Evidence still accumulates (so a later successful rewrite can pick up where this left off),
    but the statement and update_history stay untouched."""
    from api.state import make_identity_writer
    from backend.layer2_memory.identity_seed import default_identity_beliefs

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    for belief in default_identity_beliefs():
        store.save_identity(belief)
    target = next(b for b in store.identity_beliefs()
                  if b.category.value == "personality_trait" and not b.is_immutable)
    original_statement = target.statement

    class DetectsButCannotRewriteLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "revised version" in prompt:
                raise RuntimeError("generation backend unavailable")
            return (f'[{{"belief_id": "{target.belief_id}", "contradiction_score": 0.9, '
                    f'"reason": "user directly disagreed"}}]')

    write = make_identity_writer(factory, DetectsButCannotRewriteLLM())

    class C(Ctx):
        message = "that's not true about you at all"

    write(C())

    reloaded = next(b for b in store.identity_beliefs() if b.belief_id == target.belief_id)
    assert reloaded.statement == original_statement
    assert "[revised]" not in reloaded.statement
    assert len(reloaded.update_history) == 0
    assert len(reloaded.evidence_against) == 1   # evidence recorded, just no rewrite yet


def test_identity_writer_never_touches_immutable_beliefs_even_if_flagged():
    """Defense in depth: even if a (misbehaving) LLM flags an immutable belief_id, the writer
    must never rewrite it -- apply_identity_update's own immutable guard, exercised through the
    real writer against the real store."""
    from api.state import make_identity_writer
    from backend.layer2_memory.identity_seed import default_identity_beliefs

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    for belief in default_identity_beliefs():
        store.save_identity(belief)
    immutable = next(b for b in store.identity_beliefs() if b.is_immutable)
    original_statement = immutable.statement

    class MisbehavingLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return f'[{{"belief_id": "{immutable.belief_id}", "contradiction_score": 1.0, "reason": "x"}}]'

    make_identity_writer(factory, MisbehavingLLM())(Ctx())

    reloaded = next(b for b in store.identity_beliefs() if b.belief_id == immutable.belief_id)
    assert reloaded.statement == original_statement


def test_writer_reinforces_similarity_matched_recalled_memory():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    store = PostgresMemoryStore(factory)
    mem = EpisodicMemory(user_id="local-user", summary="loves hiking",
                         embedding=[0.1, 0.2, 0.3], S_current=0.5,
                         created_at=datetime.now(timezone.utc))
    store.save_episodic(mem)

    class C(Ctx):
        recalled_memories = [ScoredMemory(memory=mem, effective_score=0.9)]
    make_state_update_writer(store, FakeLLM(), factory, threshold=0.1)(C())
    assert store.get_episodic(mem.memory_id).S_current > 0.5


def test_goal_writer_persists_extracted_goal():
    from infra.db.goal_store import PostgresGoalStore
    from api.state import make_goal_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class GoalLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return '{"goal_detected": true, "new_goal": {"inferred_title": "run a 5k", "confidence": 0.8}}'

    class GoalCtx(Ctx):
        message = "I want to run a 5k next month"

    make_goal_writer(factory, GoalLLM(), FakeLLM())(GoalCtx())
    active = PostgresGoalStore(factory, "local-user").load_by_status(["active"])
    assert any(g.title == "run a 5k" for g in active)


def test_goal_writer_decomposes_a_new_goal_into_a_dated_milestone():
    """SC-5 (goal_decomposer) had zero production callers -- every goal created through the live
    pipeline had milestones=[] and deadline=None, so Layer 6's goal_checkin_item intake never
    produced a real candidate (docs/POLISH_BACKLOG.md's Layer 7 entry). This proves the fix
    through the real writer: a newly created goal is decomposed, its milestone's ISO target_date
    is parsed by the real decompose_goal, and api/proactive_gen.py::goal_checkin_item (already
    live, called every turn) can build a real GOAL_CHECK_IN item from it."""
    from infra.db.goal_store import PostgresGoalStore
    from api.state import make_goal_writer
    from api.proactive_gen import goal_checkin_item

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class GoalLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            if "goal planning specialist" in prompt:
                return ('{"milestones": [{"title": "run 1k without stopping", '
                        '"description": "first checkpoint", '
                        '"target_date": "2026-09-01T00:00:00+00:00", "progress_weight": 1.0}], '
                        '"habits": []}')
            return '{"goal_detected": true, "new_goal": {"inferred_title": "run a 5k", "confidence": 0.8}}'

    class GoalCtx(Ctx):
        message = "I want to run a 5k next month"
        now = datetime(2026, 8, 1, tzinfo=timezone.utc)

    make_goal_writer(factory, GoalLLM(), FakeLLM())(GoalCtx())
    store = PostgresGoalStore(factory, "local-user")
    active = store.load_by_status(["active"])
    goal = next(g for g in active if g.title == "run a 5k")
    assert len(goal.milestones) == 1
    assert goal.milestones[0].target_date is not None

    item = goal_checkin_item(goal, now=datetime(2026, 8, 1, tzinfo=timezone.utc))
    assert item is not None
    assert "run 1k without stopping" in item.content_basis or "first checkpoint" in item.content_basis


def test_thread_writer_persists_an_extracted_narrative_thread():
    """SC-5 (narrative-thread detector) had no producer at all -- ThreadStore's Protocol is
    read-only by design (thread_tracker.py's own docstring: records are created by a post-turn
    writer). Proves the real writer extracts and persists through PostgresThreadStore."""
    from infra.db.thread_store import PostgresThreadStore
    from api.state import make_thread_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class ThreadLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return ('{"thread_detected": true, "summary": "has a job interview coming up", '
                    '"thread_type": "future_event", "importance_tier": "high", '
                    '"confidence": 0.85, "follow_up_in_hours": 30}')

    class ThreadCtx(Ctx):
        message = "I have an interview on Thursday, kind of nervous about it"

    make_thread_writer(factory, ThreadLLM())(ThreadCtx())
    threads = PostgresThreadStore(factory, "local-user").get_all()
    assert any(t.summary == "has a job interview coming up" for t in threads)


def test_thread_writer_is_a_noop_when_no_thread_is_detected():
    from infra.db.thread_store import PostgresThreadStore
    from api.state import make_thread_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class NeutralCtx(Ctx):
        message = "the weather is nice today"

    make_thread_writer(factory, FakeLLM())(NeutralCtx())
    assert PostgresThreadStore(factory, "local-user").get_all() == []


def test_thread_proactive_writer_hands_a_due_thread_to_the_real_layer6_queue():
    """on_thread_due (backend/layer6_proactivity/intake.py) had zero production callers --
    due_threads was computed by Layer 1 but never reached the outreach queue. Proves the real
    handoff: a due NarrativeThread on ctx.input_packet becomes a real, idempotent ProactiveItem."""
    from types import SimpleNamespace
    from infra.db.proactive_store import PostgresProactiveQueue
    from api.state import make_thread_proactive_writer
    from backend.layer1_input.schemas import (
        ImportanceTier, NarrativeThread, ThreadStatus, ThreadType,
    )
    import uuid

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    thread = NarrativeThread(
        thread_id=uuid.uuid4(), summary="had a job interview", created_at=now,
        follow_up_due_at=now, status=ThreadStatus.UNRESOLVED, emotional_weight=0.7,
        importance_tier=ImportanceTier.HIGH, thread_type=ThreadType.FUTURE_EVENT)

    class ThreadDueCtx(Ctx):
        input_packet = SimpleNamespace(due_threads=[thread])

    writer = make_thread_proactive_writer(factory)
    writer(ThreadDueCtx())
    writer(ThreadDueCtx())   # idempotent: re-running the same due thread must not duplicate

    with session_scope(factory) as s:
        rows = s.query(models.ProactiveItem).filter_by(user_id="local-user").all()
    assert len(rows) == 1
    assert "had a job interview" in rows[0].payload["content_basis"]


def test_proactive_response_writer_marks_the_most_recent_sent_item_responded():
    """SC-5 (2026-08-09): a chat turn flagged is_reply_to_proactive must transition the most
    recently-sent item to RESPONDED with a real, keyword-derived valence -- there's no explicit
    item id from the client, so "most recent SENT" is the only real attribution available."""
    from api.state import make_proactive_response_writer
    from infra.db.proactive_store import PostgresProactiveQueue
    from backend.layer6_proactivity.schemas import ItemStatus, ProactiveItem

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    sent_at = datetime.now(timezone.utc) - timedelta(hours=1)
    q = PostgresProactiveQueue(factory, "local-user")
    q.upsert(ProactiveItem(item_id="older", item_type="goal_check_in",
                           status=ItemStatus.SENT.value, sent_at=sent_at - timedelta(days=1)))
    q.upsert(ProactiveItem(item_id="newest", item_type="goal_check_in",
                           status=ItemStatus.SENT.value, sent_at=sent_at))

    class ReplyCtx(Ctx):
        message = "thanks, that really helped!"
        client_metadata = {"is_reply_to_proactive": True}

    writer = make_proactive_response_writer(factory)
    writer(ReplyCtx())

    items = {i.item_id: i for i in q.load()}
    assert items["newest"].status == ItemStatus.RESPONDED.value
    assert items["newest"].user_engaged is True
    assert items["newest"].user_response_valence is not None and items["newest"].user_response_valence > 0
    assert items["older"].status == ItemStatus.SENT.value   # untouched


def test_proactive_response_writer_is_a_noop_without_the_reply_flag():
    from api.state import make_proactive_response_writer
    from infra.db.proactive_store import PostgresProactiveQueue
    from backend.layer6_proactivity.schemas import ItemStatus, ProactiveItem

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    q = PostgresProactiveQueue(factory, "local-user")
    q.upsert(ProactiveItem(item_id="p1", item_type="goal_check_in",
                           status=ItemStatus.SENT.value, sent_at=datetime.now(timezone.utc)))

    writer = make_proactive_response_writer(factory)
    writer(Ctx())   # no client_metadata flag set

    assert q.load()[0].status == ItemStatus.SENT.value


def test_thread_proactive_writer_is_a_noop_with_no_due_threads():
    from infra.db.proactive_store import PostgresProactiveQueue
    from api.state import make_thread_proactive_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    make_thread_proactive_writer(factory)(Ctx())
    with session_scope(factory) as s:
        assert s.query(models.ProactiveItem).count() == 0


def test_safety_writer_records_crisis_and_skips_none():
    from types import SimpleNamespace
    from infra.db.safety_store import PostgresSafetyLog
    from backend.layer11_safety.schemas import CrisisSignal
    from api.state import make_safety_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    writer = make_safety_writer(factory)

    def _ctx(tier):
        sig = CrisisSignal(tier=tier)
        return SimpleNamespace(user_id="local-user", session_id="s1", message="I feel awful",
                               response_text="I'm here with you.",
                               crisis_assessment=SimpleNamespace(signal=sig))

    writer(_ctx("none"))
    assert PostgresSafetyLog(factory).recent("local-user") == []
    writer(_ctx("tier_2"))
    recent = PostgresSafetyLog(factory).recent("local-user")
    assert len(recent) == 1 and recent[0].tier == "tier_2" and recent[0].user_id == "local-user"


def test_safety_writer_chains_a_real_tamper_evident_safety_record():
    """SafetyRecord's SHA-256 hash chain (architecture doc §8) had zero production callers --
    PostgresSafetyLog persisted crisis signals as plain JSONB with no cryptographic chain, so
    "safety is a verifiable property" didn't hold. Proves make_safety_writer now appends a real,
    persisted, chained SafetyRecordEntry for each crisis turn, that the chain verifies intact
    across two turns, and that a tampered row is actually detected -- not just constructed."""
    from types import SimpleNamespace
    from infra.db.safety_record_store import PostgresSafetyRecordStore
    from backend.layer11_safety.schemas import CrisisSignal
    from api.state import make_safety_writer
    import infra.db.models as m
    from infra.db.engine import session_scope

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    writer = make_safety_writer(factory)

    def _ctx(tier):
        sig = CrisisSignal(tier=tier)
        return SimpleNamespace(user_id="local-user", session_id="s1", message="I feel awful",
                               response_text="I'm here with you.",
                               crisis_assessment=SimpleNamespace(signal=sig))

    writer(_ctx("tier_1"))
    writer(_ctx("tier_2"))

    store = PostgresSafetyRecordStore(factory, "local-user")
    assert store.verify_chain() is True

    with session_scope(factory) as s:
        row = s.query(m.SafetyRecordEntry).filter_by(user_id="local-user").order_by(
            m.SafetyRecordEntry.id.asc()).first()
        payload = dict(row.payload)
        payload["detail"] = "tampered"
        row.payload = payload

    assert store.verify_chain() is False


def test_onboarding_writer_counts_and_graduates():
    from types import SimpleNamespace
    from infra.db.onboarding_store import PostgresOnboardingStore
    from api.state import make_onboarding_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    writer = make_onboarding_writer(factory, graduation_sessions=2)
    writer(SimpleNamespace(user_id="local-user", session_id="s1"))
    assert PostgresOnboardingStore(factory, "local-user").state()["cold_start_active"] is True
    writer(SimpleNamespace(user_id="local-user", session_id="s2"))
    st = PostgresOnboardingStore(factory, "local-user").state()
    assert st["session_index"] == 2 and st["cold_start_active"] is False


def test_cold_start_writer_captures_user_handle_from_a_real_message():
    """PassiveElicitationEngine/ColdStartContextBuilder had zero production callers -- Nova asks
    "what should I call you?" but nothing ever captured the answer. Proves the real writer
    captures a stated name from an ordinary message and persists it onto InitialState."""
    from infra.db.initial_state_store import PostgresInitialStateStore
    from infra.db.onboarding_store import PostgresOnboardingStore
    from api.state import make_cold_start_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    PostgresOnboardingStore(factory, "local-user", graduation_sessions=5).record_turn("s1")
    writer = make_cold_start_writer(factory, graduation_sessions=5)

    class HandleCtx(Ctx):
        message = "Hey, I'm Priya, nice to meet you"

    writer(HandleCtx())
    state = PostgresInitialStateStore(factory, "local-user").load()
    assert state.user_handle == "Priya"
    assert state.total_exchange_count == 1


def test_cold_start_writer_calibrates_emotional_baseline_and_stops_after_graduation():
    """emotional_baseline_calibrated has no real extractor in Layer 13 at all -- derived here from
    the passive engine's own emotional-style confidence ramp (>=10 messages of history). Also
    proves the writer no-ops once cold_start_active is False (never resurrects a graduated user)."""
    from infra.db.initial_state_store import PostgresInitialStateStore
    from infra.db.message_store import PostgresMessageStore
    from infra.db.onboarding_store import PostgresOnboardingStore
    from api.state import make_cold_start_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    onboarding = PostgresOnboardingStore(factory, "local-user", graduation_sessions=5)
    onboarding.record_turn("s1")
    writer = make_cold_start_writer(factory, graduation_sessions=5)
    msg_store = PostgresMessageStore(factory, "local-user")

    # Simulate the real writer chain: make_message_writer persists each turn's message BEFORE
    # make_cold_start_writer runs, so the confidence ramp has real accumulated history to read.
    for i in range(10):
        text = f"feeling anxious about work today, message {i}"
        msg_store.append("user", text, session_key="s1")

        class MsgCtx(Ctx):
            message = text
        writer(MsgCtx())


def test_cold_start_writer_graduates_early_when_real_criteria_are_all_met():
    """GraduationEvaluator's real criteria, satisfied for real (not the bare session-counter
    fallback), graduate a user ahead of make_onboarding_writer's session-count schedule."""
    from infra.db.initial_state_store import PostgresInitialStateStore
    from infra.db.onboarding_store import PostgresOnboardingStore
    from backend.layer13_onboarding.schemas import CommunicationStyleProfile
    from api.state import make_cold_start_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    onboarding = PostgresOnboardingStore(factory, "local-user", graduation_sessions=50)
    for key in ("s1", "s2", "s3"):
        onboarding.record_turn(key)   # session_index -> 3, satisfies minimum_sessions

    state_store = PostgresInitialStateStore(factory, "local-user")
    state = state_store.load()
    state.user_handle = "Priya"
    state.life_phase = "student"
    state.communication_style_profile = CommunicationStyleProfile()
    state.emotional_baseline_calibrated = True
    state.primary_topic_areas = ["work", "relationships"]
    state.total_exchange_count = 19   # one short of the required 20
    state_store.save(state)

    writer = make_cold_start_writer(factory, graduation_sessions=50)
    writer(Ctx())   # pushes total_exchange_count to 20 -> every required criterion now met

    assert onboarding.state()["cold_start_active"] is False


def test_cold_start_provider_active_then_graduated():
    from infra.db.onboarding_store import PostgresOnboardingStore
    from api.state import make_onboarding_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    provider = make_cold_start_provider(factory, graduation_sessions=1)
    # No record yet → still cold-starting → directives with observe-only overlay.
    d = provider("local-user", "hi")
    assert d is not None and d.proactivity_mode == "observe_only" and d.personality_drift_gate == 0.30
    # Advance past graduation → provider returns None (overlay self-terminates).
    make_onboarding_writer(factory, graduation_sessions=1)(
        __import__("types").SimpleNamespace(user_id="local-user", session_id="s1"))
    assert PostgresOnboardingStore(factory, "local-user").state()["cold_start_active"] is False
    assert provider("local-user", "hi") is None


def test_temporal_profile_provider_derives_from_relationship_and_message_stores():
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.message_store import PostgresMessageStore
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    rel = PostgresRelationshipStore(factory, "local-user")
    rel.record_turn("s1")
    rel.record_turn("s2")
    rel.record_turn("s3")

    msgs = PostgresMessageStore(factory, "local-user")
    msgs.append("user", "hi", session_key="s1",
                created_at=datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc))   # evening
    msgs.append("user", "still going strong", session_key="s2",
                created_at=datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc))  # evening, +4 days
    msgs.append("user", "one more", session_key="s3",
                created_at=datetime(2026, 1, 9, 20, 0, tzinfo=timezone.utc))  # evening, +4 days

    provider = make_temporal_profile_provider(factory)
    d = provider("local-user")

    assert d["total_sessions"] == 3
    assert d["relationship_age_days"] == pytest.approx(
        (datetime.now(timezone.utc) - datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)).days, abs=1)
    assert d["last_session_end"] == datetime(2026, 1, 9, 20, 0, tzinfo=timezone.utc)
    # Mean GAP BETWEEN sessions (s1->s2 and s2->s3 are both 4 days apart) — NOT
    # relationship_age_days / total_sessions, which would give a much smaller, wrong number
    # and silently defeat detect_temporal_anomaly's cadence check (see api/state.py comment).
    assert d["average_session_frequency_days"] == pytest.approx(4.0)
    # Below the minimum-sample floor (3 banded messages < 10) — stays empty rather than reporting
    # a low-confidence histogram that would flag every unseen band as "atypical".
    assert d["typical_bands"] == {}
    assert d["message_length_median_chars"] is not None


def test_temporal_profile_provider_populates_bands_above_sample_floor():
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.message_store import PostgresMessageStore
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    rel = PostgresRelationshipStore(factory, "local-user")
    msgs = PostgresMessageStore(factory, "local-user")
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(9):   # 9 evening messages
        rel.record_turn(f"s{i}")
        msgs.append("user", "evening chat", session_key=f"s{i}",
                    created_at=base.replace(day=1 + i, hour=20))
    rel.record_turn("s9")
    msgs.append("user", "morning chat", session_key="s9", created_at=base.replace(day=10, hour=9))

    d = make_temporal_profile_provider(factory)("local-user")
    assert d["typical_bands"]["evening"] == pytest.approx(0.9)
    assert d["typical_bands"]["morning"] == pytest.approx(0.1)


def test_temporal_profile_provider_applies_timezone_offset_to_band_histogram():
    """The historical band histogram must apply the same timezone_offset_hours as the live
    circadian band computed in api/assembly.py::perceive, or the two silently diverge
    (docs/layer-1-architecture.md §16, 'Circadian histogram is UTC-based')."""
    from infra.db.relationship_store import PostgresRelationshipStore
    from infra.db.message_store import PostgresMessageStore
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    rel = PostgresRelationshipStore(factory, "local-user")
    msgs = PostgresMessageStore(factory, "local-user")
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # 20:00 UTC == 01:30 IST (+5:30) the next day — "evening" in UTC, "late_night" in IST.
    for i in range(10):
        rel.record_turn(f"s{i}")
        msgs.append("user", "message", session_key=f"s{i}", created_at=base.replace(day=1 + i, hour=20))

    utc_bands = make_temporal_profile_provider(factory)("local-user")["typical_bands"]
    ist_bands = make_temporal_profile_provider(factory, 5.5)("local-user")["typical_bands"]

    assert utc_bands == {"evening": pytest.approx(1.0)}
    assert ist_bands == {"late_night": pytest.approx(1.0)}


def test_temporal_profile_provider_empty_history_yields_no_bands():
    from api.state import make_temporal_profile_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    d = make_temporal_profile_provider(factory)("brand-new-user")
    assert d["total_sessions"] == 0
    assert d["relationship_age_days"] == 0
    assert d["typical_bands"] == {}
    assert d["last_session_end"] is None
    assert d["message_length_median_chars"] is None


def test_session_last_delivered_provider_reads_real_persisted_timestamp():
    """Layer 1 SC-2's latency signal source: Session.last_delivered_at is stamped by
    make_state_update_writer's Session upsert and read back here for the *next* turn's
    perceive() -- proves the round-trip through the real store, not a mock."""
    from datetime import datetime, timezone
    from api.state import make_session_last_delivered_provider
    import infra.db.models as models
    from infra.db.engine import session_scope

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    provider = make_session_last_delivered_provider(factory)

    assert provider("s1") is None                            # no session row yet

    stamped = datetime(2026, 8, 9, 10, 0, tzinfo=timezone.utc)
    with session_scope(factory) as s:
        s.add(models.Session(user_id="u1", session_key="s1", turn_count=1,
                             last_delivered_at=stamped))
    assert provider("s1") == stamped
    assert provider("s2") is None                             # a different session, still cold


def test_life_event_writer_persists_an_extracted_life_event():
    """No LifeEvent detector existed anywhere -- detect_chapter_boundaries was real and callable
    but always received life_events=[]. Proves the real writer extracts and persists through
    PostgresLongitudinalStore."""
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from api.state import make_life_event_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class LifeEventLLM(FakeLLM):
        def complete(self, prompt, *, system=None, temperature=None, max_tokens=None):
            return ('{"life_event_detected": true, "title": "started a new job", '
                    '"category": "career_transition", "event_date": "2026-08-09", '
                    '"significance_score": 0.8, "confidence": 0.85}')

    class LifeEventCtx(Ctx):
        message = "I started a new job this week, feeling good about it"

    make_life_event_writer(factory, LifeEventLLM())(LifeEventCtx())
    events = PostgresLongitudinalStore(factory, "local-user").life_events()
    assert any(e.title == "started a new job" for e in events)


def test_life_event_writer_is_a_noop_when_no_event_is_detected():
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from api.state import make_life_event_writer

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)

    class NeutralCtx(Ctx):
        message = "the weather is nice today"

    make_life_event_writer(factory, FakeLLM())(NeutralCtx())
    assert PostgresLongitudinalStore(factory, "local-user").life_events() == []


def test_longitudinal_provider_populates_primary_goals_deadlines_and_recent_life_event():
    """primary_active_goals/upcoming_goal_deadlines/recent_life_event were all real,
    already-accepted assemble_context_packet params that make_longitudinal_provider never passed.
    Proves all three reach the real Layer10ContextPacket through the real provider."""
    from datetime import date, timedelta
    from infra.db.longitudinal_store import PostgresLongitudinalStore
    from infra.db.goal_store import PostgresGoalStore
    from infra.db.relationship_store import PostgresRelationshipStore
    from backend.layer7_goals.schemas import Goal, Milestone
    from backend.layer10_longitudinal.schemas import LifeEvent
    from api.state import make_longitudinal_provider

    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    factory = make_session_factory(engine)
    now = datetime.now(timezone.utc)

    PostgresRelationshipStore(factory, "local-user").record_turn("s1")   # seeds first_session_date
    PostgresGoalStore(factory, "local-user").add_goal(Goal(
        title="run a 5k", status="active", emotional_weight=0.9, created_at=now,
        milestones=[Milestone(description="first 1k", target_date=now + timedelta(days=5))]))
    PostgresLongitudinalStore(factory, "local-user").save_life_event(LifeEvent(
        event_id="e1", user_id="local-user", title="started a new job",
        category="career_transition", event_date=date.today()))

    packet = make_longitudinal_provider(factory)("local-user", now=now)

    assert "run a 5k" in packet.primary_active_goals
    assert any(title == "run a 5k" for title, _ in packet.upcoming_goal_deadlines)
    assert packet.recent_life_event is not None
    assert packet.recent_life_event.title == "started a new job"
