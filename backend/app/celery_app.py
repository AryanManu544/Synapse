import ssl
from urllib.parse import urlparse

import certifi
from celery import Celery  # type: ignore[import-untyped]

from app.core.config import get_settings

settings = get_settings()


def _redis_ssl_options(url: str) -> dict[str, int | str] | None:
    """Upstash and other hosted Redis brokers use TLS (`rediss://`)."""
    if urlparse(url).scheme != "rediss":
        return None
    # CERT_NONE was dangerous here: MITM could read or modify task payloads.
    return {"ssl_cert_reqs": ssl.CERT_REQUIRED, "ssl_ca_certs": certifi.where()}


celery_app = Celery(
    "synapse",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.review_tasks"],
)

_broker_ssl = _redis_ssl_options(settings.celery_broker_url)
_backend_ssl = _redis_ssl_options(settings.celery_result_backend)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.celery_worker_concurrency,
    worker_max_tasks_per_child=50,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_reject_on_worker_lost=True,
    task_default_queue="reviews",
    **({"broker_use_ssl": _broker_ssl} if _broker_ssl else {}),
    **({"redis_backend_use_ssl": _backend_ssl} if _backend_ssl else {}),
)
