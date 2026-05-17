from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import psycopg_connect_args


def _to_sync_database_url(async_url: str) -> str:
    """Convert async SQLAlchemy URL to a sync driver URL."""
    if async_url.startswith("postgresql+asyncpg://"):
        sync_url = async_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        return sync_url.replace("ssl=require", "sslmode=require")
    return async_url


@lru_cache
def get_sync_engine() -> Engine:
    settings = get_settings()
    database_url = _to_sync_database_url(str(settings.database_url))
    engine_kwargs: dict = {"pool_pre_ping": True}
    if connect_args := psycopg_connect_args(str(settings.database_url)):
        engine_kwargs["connect_args"] = connect_args
    return create_engine(database_url, **engine_kwargs)


@lru_cache
def get_sync_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_sync_engine(), expire_on_commit=False)


def get_sync_session() -> Generator[Session, None, None]:
    """Yield a sync ORM session (for Celery workers)."""
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
