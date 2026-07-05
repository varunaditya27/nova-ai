"""Relational (Postgres) infrastructure — declarative base, engine, session scope.

Re-exports are lazy (PEP 562) so pure submodules like ``memory_serde`` import on a bare
interpreter without pulling in SQLAlchemy — matching ``infra/vector_store``'s pattern.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["Base", "make_engine", "make_session_factory", "session_scope", "init_db"]

if TYPE_CHECKING:  # for type checkers only; not executed at runtime
    from infra.db.base import Base
    from infra.db.engine import init_db, make_engine, make_session_factory, session_scope

_LAZY = {
    "Base": ("infra.db.base", "Base"),
    "make_engine": ("infra.db.engine", "make_engine"),
    "make_session_factory": ("infra.db.engine", "make_session_factory"),
    "session_scope": ("infra.db.engine", "session_scope"),
    "init_db": ("infra.db.engine", "init_db"),
}


def __getattr__(name: str):
    import importlib
    if name in _LAZY:
        mod, attr = _LAZY[name]
        return getattr(importlib.import_module(mod), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
