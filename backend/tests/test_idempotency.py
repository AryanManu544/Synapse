import fakeredis

from app.core.config import Settings
from app.core.idempotency import ReviewIdempotencyLock


def _make_lock() -> ReviewIdempotencyLock:
    settings = Settings(
        redis_url="redis://localhost:6379/0",
        review_lock_processing_ttl_seconds=60,
        review_lock_completed_ttl_seconds=120,
    )
    lock = ReviewIdempotencyLock(settings)
    lock._client = fakeredis.FakeRedis(decode_responses=True)
    return lock


def test_idempotency_lock_acquire_and_complete() -> None:
    lock = _make_lock()
    repo = "org/repo"
    sha = "abc123"

    assert lock.try_acquire(repo, sha) is True
    assert lock.is_locked(repo, sha) is True
    assert lock.try_acquire(repo, sha) is False

    lock.mark_completed(repo, sha)
    assert lock.is_locked(repo, sha) is True

    lock.release(repo, sha)
    assert lock.is_locked(repo, sha) is False
    assert lock.try_acquire(repo, sha) is True
