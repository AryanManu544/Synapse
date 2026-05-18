import ssl
from urllib.parse import urlparse

import redis

from app.core.config import Settings


def create_redis_client(settings: Settings) -> redis.Redis:
    """Redis client with TLS options for Upstash (`rediss://`)."""
    url = str(settings.redis_url)
    kwargs: dict = {"decode_responses": True}
    if urlparse(url).scheme == "rediss":
        kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
    return redis.Redis.from_url(url, **kwargs)
