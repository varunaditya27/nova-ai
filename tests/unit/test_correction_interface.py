"""Tests for SC-3 Memory Correction Interface (architecture doc §5.5)."""

from datetime import date
from types import SimpleNamespace

from backend.layer12_privacy import correction_interface as ci
from backend.layer12_privacy.schemas import (
    CorrectionResult,
    MemoryCorrectionRequest,
    MemoryCorrectionType,
)


class FakeStore:
    def __init__(self, mem):
        self._m = {mem.memory_id: mem}
    def get(self, mid):
        return self._m.get(mid)
    def update(self, mid, fields):
        for k, v in fields.items():
            setattr(self._m[mid], k, v)


def _mem(**kw):
    base = dict(memory_id="m1", content="old", importance_score=0.8, topic_tags=["a", "b"],
                is_anchored=False, decay_rate=0.1, is_user_confirmed=False)
    base.update(kw)
    return SimpleNamespace(**base)


def _apply(req, mem=None, embed_fn=None, audit_log=None):
    mem = mem or _mem()
    store = FakeStore(mem)
    res = ci.apply_correction(req, store, embed_fn=embed_fn, audit_log=audit_log)
    return res, store.get(mem.memory_id)


def test_edit_updates_content_and_confirms():
    req = MemoryCorrectionRequest(memory_id="m1", correction_type=MemoryCorrectionType.EDIT.value,
                                  new_content="corrected")
    res, mem = _apply(req, embed_fn=lambda t: [0.1, 0.2])
    assert isinstance(res, CorrectionResult) and res.success
    assert mem.content == "corrected" and mem.is_user_confirmed is True
    assert mem.embedding == [0.1, 0.2]


def test_downgrade_lowers_importance():
    req = MemoryCorrectionRequest(memory_id="m1", correction_type=MemoryCorrectionType.DOWNGRADE.value,
                                  new_importance="Low")
    _, mem = _apply(req)
    assert mem.importance_score == 0.20


def test_decontextualize_removes_tags():
    req = MemoryCorrectionRequest(memory_id="m1",
                                  correction_type=MemoryCorrectionType.DECONTEXTUALIZE.value,
                                  tags_to_remove=["a"])
    _, mem = _apply(req)
    assert mem.topic_tags == ["b"]


def test_anchor_sets_no_decay_and_high_importance():
    req = MemoryCorrectionRequest(memory_id="m1", correction_type=MemoryCorrectionType.ANCHOR.value)
    _, mem = _apply(req)
    assert mem.is_anchored is True and mem.decay_rate == 0.0 and mem.importance_score >= 0.95


def test_expire_sets_auto_expiry_date():
    req = MemoryCorrectionRequest(memory_id="m1", correction_type=MemoryCorrectionType.EXPIRE.value,
                                  expiry_date=date(2026, 1, 1))
    _, mem = _apply(req)
    assert mem.auto_expiry_date == date(2026, 1, 1)


def test_confirm_marks_user_confirmed():
    req = MemoryCorrectionRequest(memory_id="m1", correction_type=MemoryCorrectionType.CONFIRM.value)
    _, mem = _apply(req)
    assert mem.is_user_confirmed is True


def test_correction_is_logged():
    log = []
    req = MemoryCorrectionRequest(memory_id="m1", correction_type=MemoryCorrectionType.CONFIRM.value)
    _apply(req, audit_log=log)
    assert len(log) == 1 and log[0]["memory_id"] == "m1"


def test_unknown_memory_is_graceful():
    store = FakeStore(_mem())
    req = MemoryCorrectionRequest(memory_id="nope", correction_type=MemoryCorrectionType.CONFIRM.value)
    res = ci.apply_correction(req, store)
    assert res.success is False
