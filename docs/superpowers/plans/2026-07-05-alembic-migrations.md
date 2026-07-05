# Alembic Migrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add Alembic as the versioned-migration mechanism for the Postgres schema, with a `create_all`-based baseline and a parity test keeping it in lockstep with the ORM models.

**Architecture:** A standard Alembic scaffold (`alembic.ini` + `migrations/`) whose baseline migration calls `Base.metadata.create_all`/`drop_all` (zero drift). `create_all`/`init_db` stays for the offline test suite; production uses `alembic upgrade head`.

**Tech Stack:** Alembic 1.13+, SQLAlchemy 2.x, pytest.

## Global Constraints

- Run alembic/sqlalchemy tests with `.venv/bin/python -m pytest`; the migration test starts `pytest.importorskip("alembic")`.
- **Offline invariant:** `/usr/bin/python3.11 -m pytest tests/ -q` stays green — the migration test skips (alembic not on the system interpreter), and **no production code imports alembic**.
- Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Branch: `alembic-migrations` (checked out; spec committed).

---

### Task 1: Alembic scaffold + baseline migration + parity test

**Files:**
- Modify: `pyproject.toml` (add `alembic>=1.13` to the `infra` extra)
- Create: `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_baseline_schema.py`
- Test: `tests/integration_infra/test_migrations.py`

- [ ] **Step 1: Write the failing test** — `tests/integration_infra/test_migrations.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/integration_infra/test_migrations.py -q`
Expected: FAIL/ERROR — `alembic.util.exc.CommandError` / missing `alembic.ini`.

- [ ] **Step 3: Add the dependency** — in `pyproject.toml`, add `"alembic>=1.13"` to the `infra` optional-dependencies list, then install: `.venv/bin/pip install "alembic>=1.13"`.

- [ ] **Step 4: Create `alembic.ini`:**

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+psycopg://nova:nova@127.0.0.1:5432/nova

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 5: Create `migrations/env.py`:**

```python
"""Alembic environment: target = infra.db Base.metadata; URL from NOVA_DATABASE_URL or alembic.ini."""
from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from infra.db.base import Base
import infra.db.models  # noqa: F401 — register every table on Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_env_url = os.environ.get("NOVA_DATABASE_URL")
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
        literal_binds=True, render_as_batch=True, compare_type=True,
        dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.",
        poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6: Create `migrations/script.py.mako`:**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 7: Create `migrations/versions/0001_baseline_schema.py`:**

```python
"""baseline schema — full current model set via create_all

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-05
"""
from alembic import op

from infra.db.base import Base
import infra.db.models  # noqa: F401 — register every table

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
```

- [ ] **Step 8: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/integration_infra/test_migrations.py -q`
Expected: PASS (2 passed).
Also verify against live Postgres (optional): `docker compose -f docker/docker-compose.yml up -d postgres && .venv/bin/python -m alembic upgrade head` (from repo root) → `Running upgrade -> 0001_baseline`.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml alembic.ini migrations/ tests/integration_infra/test_migrations.py
git commit -m "feat(infra): Alembic migrations with create_all baseline

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Docs + full gate

**Files:**
- Modify: `CLAUDE.md` (Commands + Infrastructure/DB note)
- Modify: `docs/superpowers/specs/2026-07-05-alembic-migrations-design.md` (Status → Implemented)

- [ ] **Step 1: Update CLAUDE.md** — in the Commands section add:
```bash
# Apply DB migrations (production/persistent DB; tests use create_all)
alembic upgrade head
```
In the Relational DB / Infrastructure note, state that the persistent schema is managed by
`alembic upgrade head` (baseline `migrations/versions/0001_baseline_schema.py` via `create_all`);
`init_db` remains the fast create-all path for the offline test suite and ad-hoc bootstrap.

- [ ] **Step 2: Spec status** — change `**Status:** Approved (design)` to `**Status:** Implemented`.

- [ ] **Step 3: Full gate**

Run: `/usr/bin/python3.11 -m pytest tests/ -q` → green (migration test skips; nothing regresses).
Run: `.venv/bin/python -m pytest tests/ -q -m "not docker"` → all pass (incl. the migration test).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-07-05-alembic-migrations-design.md
git commit -m "docs: document alembic upgrade head as the production schema path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes (author)

- **Spec coverage:** §3.1 dep → Task 1 Step 3; §3.2 scaffold → Steps 4–6; §3.3 baseline → Step 7;
  §3.4 docs → Task 2; §4 parity/downgrade tests → Task 1 Steps 1–2,8.
- **Offline invariant:** the only alembic import in the tree lives in `migrations/` + the
  `importorskip`-guarded test; no `api`/`infra`/`backend` runtime module imports alembic.
- **env.py URL precedence:** `NOVA_DATABASE_URL` overrides the ini; the parity test `delenv`s it so the
  temp-SQLite url set via `set_main_option` wins.
