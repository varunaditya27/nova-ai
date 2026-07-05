import pytest
pytest.importorskip("alembic")
pytest.importorskip("sqlalchemy")

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from infra.db.base import Base
import infra.db.models  # noqa: F401 — register all tables

ROOT = Path(__file__).resolve().parents[2]


def _cfg(db_path, monkeypatch):
    monkeypatch.delenv("NOVA_DATABASE_URL", raising=False)
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path}")
    return cfg


def test_upgrade_head_matches_metadata(tmp_path, monkeypatch):
    db = tmp_path / "m.db"
    command.upgrade(_cfg(db, monkeypatch), "head")
    tables = set(inspect(create_engine(f"sqlite+pysqlite:///{db}")).get_table_names())
    assert set(Base.metadata.tables) <= tables
    assert "alembic_version" in tables


def test_downgrade_base_is_clean(tmp_path, monkeypatch):
    db = tmp_path / "m.db"
    cfg = _cfg(db, monkeypatch)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    remaining = set(inspect(create_engine(f"sqlite+pysqlite:///{db}")).get_table_names()) - {"alembic_version"}
    assert remaining == set()
