from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import (  # noqa: F401  (register metadata)
    AuditLog,
    Consent,
    Recording,
    Synthesis,
    User,
    VoiceProfile,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Only fall back to settings if the caller didn't set sqlalchemy.url
# (tests pass a different URL pointing to vcapp_test).
if not config.get_main_option("sqlalchemy.url"):
    _s = get_settings()
    _sync_url = (
        f"postgresql+psycopg2://{_s.postgres_user}:{_s.postgres_password}"
        f"@{_s.postgres_host}:{_s.postgres_port}/{_s.postgres_db}"
    )
    config.set_main_option("sqlalchemy.url", _sync_url)
_sync_url = config.get_main_option("sqlalchemy.url")

target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in {"app", "audit"}
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
