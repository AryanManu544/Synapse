import ssl
from urllib.parse import urlparse

import certifi
import redis

from app.core.config import Settings


def create_redis_client(settings: Settings) -> redis.Redis:
    """Redis client with TLS options for Upstash (`rediss://`)."""
    url = str(settings.redis_url)
    kwargs: dict[str, object] = {"decode_responses": True}
    if urlparse(url).scheme == "rediss":
        # CERT_NONE was dangerous here: MITM could read or modify task payloads.
        kwargs["ssl_cert_reqs"] = ssl.CERT_REQUIRED
        kwargs["ssl_ca_certs"] = certifi.where()
    return redis.Redis.from_url(url, **kwargs)
