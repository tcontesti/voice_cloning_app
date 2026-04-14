"""Shared test fixtures.

Tests use a separate database `vcapp_test` created on session start.
Each test runs inside a SAVEPOINT-style transaction that is rolled back at
teardown so tests are isolated.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

TEST_DB = "vcapp_test"


def _admin_url() -> str:
    s = get_settings()
    return (
        f"postgresql+psycopg2://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/postgres"
    )


def _test_async_url() -> str:
    s = get_settings()
    return (
        f"postgresql+asyncpg://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/{TEST_DB}"
    )


def _test_sync_url() -> str:
    s = get_settings()
    return (
        f"postgresql+psycopg2://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/{TEST_DB}"
    )


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db() -> Iterator[None]:
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    admin.dispose()

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _test_sync_url())
    command.upgrade(cfg, "head")

    yield

    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
    admin.dispose()


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Per-test async engine + connection + outer transaction. Rollback at end.

    Engine is created per test to avoid event-loop binding issues that occur
    when a session-scoped engine is reused across function-scoped event loops
    in pytest-asyncio default config.
    """
    engine = create_async_engine(_test_async_url(), pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            async with Session(bind=conn) as s:
                try:
                    yield s
                finally:
                    await trans.rollback()
    finally:
        await engine.dispose()
