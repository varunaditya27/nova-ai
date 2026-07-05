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
