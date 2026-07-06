import pytest
pytest.importorskip("sqlalchemy")

from infra.db.ann_recall_store import AnnRecallStore


class FakeBase:
    def __init__(self):
        self.linear_called = False
        self._eps = {}
        self.semantic = []
    def candidate_memories(self, user_id):
        self.linear_called = True
        return ["LINEAR"]
    def get_episodic(self, mid):
        return self._eps.get(mid)
    def active_semantic(self, user_id):
        return list(self.semantic)


class Ep:
    def __init__(self, mid, deleted=False):
        self.memory_id = mid
        self.is_deleted = deleted


class FakeVS:
    def __init__(self, hits=None, boom=False):
        self._hits = hits or []
        self._boom = boom
    def query(self, collection, embedding, n_results=3, where=None):
        if self._boom:
            raise RuntimeError("chroma down")
        return self._hits


def test_ann_hydrates_hit_ids():
    base = FakeBase()
    base._eps = {"m1": Ep("m1"), "m2": Ep("m2")}
    vs = FakeVS(hits=[{"id": "m1"}, {"id": "m2"}])
    store = AnnRecallStore(base, vs, [0.1, 0.2], "u1")
    cands = store.candidate_memories("u1")
    assert [c.memory_id for c in cands] == ["m1", "m2"]
    assert base.linear_called is False


def test_ann_skips_deleted_and_appends_semantic():
    base = FakeBase()
    base._eps = {"m1": Ep("m1"), "m2": Ep("m2", deleted=True)}
    base.semantic = ["SEM"]
    vs = FakeVS(hits=[{"id": "m1"}, {"id": "m2"}])
    cands = AnnRecallStore(base, vs, [0.1], "u1").candidate_memories("u1")
    assert [getattr(c, "memory_id", c) for c in cands] == ["m1", "SEM"]


def test_falls_back_to_linear_on_empty_index():
    base = FakeBase()
    cands = AnnRecallStore(base, FakeVS(hits=[]), [0.1], "u1").candidate_memories("u1")
    assert cands == ["LINEAR"] and base.linear_called is True


def test_falls_back_to_linear_on_vector_store_error():
    base = FakeBase()
    cands = AnnRecallStore(base, FakeVS(boom=True), [0.1], "u1").candidate_memories("u1")
    assert cands == ["LINEAR"] and base.linear_called is True


def test_delegates_other_methods_to_base():
    base = FakeBase()
    base._eps = {"m1": Ep("m1")}
    store = AnnRecallStore(base, FakeVS(), [0.1], "u1")
    assert store.get_episodic("m1").memory_id == "m1"   # delegated via __getattr__
