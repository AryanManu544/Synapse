from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.core.database import asyncpg_connect_args

# Pool defaults are split 3 async + 2 sync = 5 total base connections,
# matching the Supabase free tier connection limit.
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine(settings: Settings | None = None) -> AsyncEngine:
    """Lazy-initialize async SQLAlchemy engine."""
    global _engine, _session_factory
    if settings is None:
        settings = get_settings()
    if _engine is None:
        database_url = str(settings.database_url)
        engine_kwargs: dict[str, object] = {
            "echo": settings.debug,
            "pool_pre_ping": True,
            "pool_size": settings.db_pool_size_async,
            "max_overflow": 2,
            "pool_timeout": 10,
            "pool_recycle": 1800,
        }
        if connect_args := asyncpg_connect_args(database_url):
            engine_kwargs["connect_args"] = connect_args
        _engine = create_async_engine(database_url, **engine_kwargs)
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


async def get_db_session(
    _settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session per request."""
    get_async_engine(_settings)
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")
    async with _session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory, initializing the engine if needed."""
    get_async_engine(get_settings())
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")
    return _session_factory


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
