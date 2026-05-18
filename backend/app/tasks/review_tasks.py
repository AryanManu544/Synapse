from __future__ import annotations

from typing import Any

from celery import Task

from app.celery_app import celery_app
from app.tasks.review_runner import execute_pr_review


@celery_app.task(
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
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            return {"status": "failed", "record_id": record_id, "error": str(exc)}
        raise self.retry(exc=exc) from exc
