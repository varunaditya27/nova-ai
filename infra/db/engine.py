"""Postgres engine, session factory, and transactional scope."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infra.db.base import Base


def make_engine(url: str):
    return create_engine(url, future=True, pool_pre_ping=True)


def make_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine) -> None:
    """Create all tables (dev/bootstrap path; Alembic migrations are a later increment)."""
    import infra.db.models  # noqa: F401 — ensure all models are registered on Base.metadata
    Base.metadata.create_all(engine)
