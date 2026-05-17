import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import make_url
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.deps import get_async_engine
from app.core.logging import configure_logging
from app.models.orm.base import Base
from app.core.deps import get_session_factory
from app.models.orm import pull_request, review_finding, review_rules  # noqa: F401
from app.services.dashboard_service import seed_default_rules

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    configure_logging(debug=settings.debug, log_format=settings.log_format)
    db = make_url(settings.database_url)
    logger.info(
        "Database target user=%s host=%s port=%s database=%s",
        db.username,
        db.host,
        db.port,
        db.database,
    )
    engine = get_async_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed_default_rules(session)

    yield


def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
