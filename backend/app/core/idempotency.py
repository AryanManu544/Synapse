import logging

from app.core.config import Settings
from app.core.redis_client import create_redis_client

logger = logging.getLogger(__name__)

LOCK_KEY_PREFIX = "pr_review:lock:"


class ReviewIdempotencyLock:
    """Redis-backed lock to prevent duplicate processing of the same commit SHA."""

    def __init__(self, settings: Settings) -> None:
        self._client = create_redis_client(settings)
        self._processing_ttl = settings.review_lock_processing_ttl_seconds
        self._completed_ttl = settings.review_lock_completed_ttl_seconds

    @staticmethod
    def _key(repository_full_name: str, head_sha: str) -> str:
        return f"{LOCK_KEY_PREFIX}{repository_full_name}:{head_sha}"

    def is_locked(self, repository_full_name: str, head_sha: str) -> bool:
        """Return True when a commit is already being processed or was completed."""
        return bool(self._client.exists(self._key(repository_full_name, head_sha)))

    def try_acquire(self, repository_full_name: str, head_sha: str) -> bool:
        """
        Acquire a processing lock for a repository commit.

        Returns True when this caller should process the commit; False if already
        locked or completed.
        """
        acquired = self._client.set(
            self._key(repository_full_name, head_sha),
            "processing",
            nx=True,
            ex=self._processing_ttl,
        )
        if not acquired:
            logger.info(
                "Skipping duplicate review for %s@%s (lock held)",
                repository_full_name,
                head_sha[:7],
            )
        return bool(acquired)

    def mark_completed(self, repository_full_name: str, head_sha: str) -> None:
        """Mark a commit review as successfully completed."""
        self._client.set(
            self._key(repository_full_name, head_sha),
            "completed",
            ex=self._completed_ttl,
        )

    def release(self, repository_full_name: str, head_sha: str) -> None:
        """Release the lock so a failed job may be retried."""
        self._client.delete(self._key(repository_full_name, head_sha))
        logger.info(
            "Released review lock for %s@%s",
            repository_full_name,
            head_sha[:7],
        )
