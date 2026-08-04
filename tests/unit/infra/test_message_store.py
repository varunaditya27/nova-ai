import pytest
pytest.importorskip("sqlalchemy")

from datetime import datetime, timedelta, timezone

from infra.db.engine import make_engine, make_session_factory, init_db
from infra.db.message_store import PostgresMessageStore


def _store(user="u1"):
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return PostgresMessageStore(make_session_factory(engine), user)


def test_append_and_history_is_newest_first():
    st = _store()
    st.append("user", "hi")
    st.append("nova", "hello there", echoes=[{"summary": "past thing", "when": "last week"}])
    hist = st.history()
    assert [h["role"] for h in hist] == ["nova", "user"]        # newest first
    assert hist[0]["echoes"][0]["summary"] == "past thing"


def test_history_pagination_by_before_id():
    st = _store()
    for i in range(5):
        st.append("user", f"m{i}")
    page1 = st.history(limit=2)
    assert [h["content"] for h in page1] == ["m4", "m3"]
    page2 = st.history(limit=2, before_id=page1[-1]["row_id"])
    assert [h["content"] for h in page2] == ["m2", "m1"]


def test_keyword_search():
    st = _store()
    st.append("user", "I love the hackathon")
    st.append("user", "unrelated message")
    hits = st.search(query="hackathon")
    assert len(hits) == 1 and "hackathon" in hits[0]["content"]


def test_search_escapes_like_wildcards():
    st = _store()
    st.append("user", "100% sure about this")
    st.append("user", "totally unrelated")
    # A literal '%' must not act as a SQL wildcard matching everything.
    assert len(st.search(query="%")) == 1
    assert st.search(query="%")[0]["content"].startswith("100%")


def test_date_range_search():
    st = _store()
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = datetime(2026, 7, 1, tzinfo=timezone.utc)
    st.append("user", "old one", created_at=old)
    st.append("user", "new one", created_at=new)
    hits = st.search(start=datetime(2026, 6, 1, tzinfo=timezone.utc))
    assert len(hits) == 1 and hits[0]["content"] == "new one"


def test_bookmark_and_list():
    st = _store()
    mid = st.append("user", "a keeper")
    assert st.set_bookmark(mid, True, category="Idea") is True
    marks = st.list_bookmarks()
    assert len(marks) == 1 and marks[0]["bookmark_category"] == "Idea"
    assert st.list_bookmarks(category="Funny") == []
    st.set_bookmark(mid, False)
    assert st.list_bookmarks() == []


def test_milestone_and_list():
    st = _store()
    mid = st.append("user", "We launched!")
    st.set_milestone(mid, True, label="Launch")
    ms = st.list_milestones()
    assert len(ms) == 1 and ms[0]["milestone_label"] == "Launch"


def test_set_flag_on_missing_message_is_false():
    assert _store().set_bookmark("nope", True) is False


def test_count_first_last_and_user_scope():
    st = _store()
    st.append("user", "first msg")
    st.append("nova", "reply")
    assert st.count() == 2
    assert st.first()["content"] == "first msg"
    assert st.last_interaction_at() is not None
    # user scope: another user sees nothing
    other = PostgresMessageStore(st._sf, "u2")
    assert other.count() == 0


def test_day_activity_groups_by_date():
    st = _store()
    d = datetime(2026, 7, 7, 9, tzinfo=timezone.utc)
    st.append("user", "a", created_at=d)
    st.append("nova", "b", created_at=d + timedelta(hours=1))
    st.append("user", "c", created_at=d + timedelta(days=1))
    counts = st.day_activity(datetime(2026, 7, 1, tzinfo=timezone.utc),
                             datetime(2026, 7, 31, tzinfo=timezone.utc))
    assert counts["2026-07-07"] == 2 and counts["2026-07-08"] == 1


def test_day_activity_applies_timezone_offset():
    """A message at 20:00 UTC is already the next calendar day in IST (+5:30) -- the heatmap
    must bucket by local date, matching Layer 1's live circadian-band offset (see
    docs/layer-1-architecture.md §16)."""
    st = _store()
    st.append("user", "late night IST", created_at=datetime(2026, 7, 7, 20, 0, tzinfo=timezone.utc))

    utc_counts = st.day_activity(datetime(2026, 7, 1, tzinfo=timezone.utc),
                                 datetime(2026, 7, 31, tzinfo=timezone.utc))
    ist_counts = st.day_activity(datetime(2026, 7, 1, tzinfo=timezone.utc),
                                 datetime(2026, 7, 31, tzinfo=timezone.utc),
                                 timezone_offset_hours=5.5)

    assert utc_counts == {"2026-07-07": 1}
    assert ist_counts == {"2026-07-08": 1}


def test_day_activity_local_date_key_can_extend_past_end_boundary():
    """Documented boundary behavior: start/end filter the underlying UTC timestamps, not the
    returned local-date keys, so a message just inside `end` can bucket into a local date one
    day past `end`'s calendar date (see day_activity's docstring)."""
    st = _store()
    boundary_end = datetime(2026, 7, 31, 23, 59, tzinfo=timezone.utc)
    # 22:00 UTC on the last day == 2026-08-01 03:30 IST -- inside the UTC filter, but its local
    # date key falls one day past `end`'s calendar date.
    st.append("user", "late", created_at=datetime(2026, 7, 31, 22, 0, tzinfo=timezone.utc))

    counts = st.day_activity(datetime(2026, 7, 1, tzinfo=timezone.utc), boundary_end,
                             timezone_offset_hours=5.5)
    assert counts == {"2026-08-01": 1}
