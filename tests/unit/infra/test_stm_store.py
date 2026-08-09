from backend.layer2_memory.schemas import ShortTermMemoryBuffer
from infra.stm_store import InProcessSTMStore


def test_get_or_create_returns_same_buffer_across_calls():
    store = InProcessSTMStore()
    a = store.get_or_create("s1", "u1")
    b = store.get_or_create("s1", "u1")
    assert a is b


def test_get_or_create_creates_independent_buffers_per_session():
    store = InProcessSTMStore()
    a = store.get_or_create("s1", "u1")
    b = store.get_or_create("s2", "u1")
    assert a is not b


def test_save_replaces_the_stored_buffer():
    store = InProcessSTMStore()
    store.get_or_create("s1", "u1")
    new_buf = ShortTermMemoryBuffer(session_id="s1", user_id="u1")
    store.save("s1", new_buf)
    assert store.get("s1") is new_buf


def test_get_returns_none_for_unknown_session():
    store = InProcessSTMStore()
    assert store.get("unknown") is None
