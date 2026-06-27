from __future__ import annotations

from typing import Any

from billiard.exceptions import SoftTimeLimitExceeded  # type: ignore[import-untyped]
from celery import Task  # type: ignore[import-untyped]

from app.celery_app import celery_app
from app.db.sync_session import get_sync_session_factory
from app.services.review_persistence import mark_review_failed
from app.tasks.review_runner import execute_pr_review


@celery_app.task(  # type: ignore[untyped-decorator]
    name="process_pr_review",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_pr_review(
    self: Task,
    *,
    record_id: str,
    installation_id: int,
    repository_full_name: str,
    pr_number: int,
    head_sha: str,
) -> dict[str, Any]:
    """Celery entrypoint (local Docker Compose). Retries on transient failures."""
    try:
        result = execute_pr_review(
            record_id=record_id,
            installation_id=installation_id,
            repository_full_name=repository_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
        )
        if result["status"] == "failed" and self.request.retries < self.max_retries:
            raise RuntimeError(result.get("error", "review failed"))
        return result
    except SoftTimeLimitExceeded:
        session_factory = get_sync_session_factory()
        with session_factory() as session:
            mark_review_failed(session, record_id, "Review timed out after 5 minutes")
        raise
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            return {"status": "failed", "record_id": record_id, "error": str(exc)}
        raise self.retry(exc=exc) from exc
