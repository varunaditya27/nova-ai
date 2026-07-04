import pytest
pytest.importorskip("sqlalchemy")

from sqlalchemy import text

from infra.db.engine import make_engine, make_session_factory, session_scope


def test_session_scope_commits_and_closes():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        result = session.execute(text("select 1")).scalar_one()
    assert result == 1


def test_session_scope_rolls_back_on_error():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    factory = make_session_factory(engine)
    with pytest.raises(ValueError):
        with session_scope(factory) as session:
            session.execute(text("select 1"))
            raise ValueError("boom")
    # the context manager must not swallow the error
