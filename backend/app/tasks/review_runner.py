"""PR review orchestration (used by Celery locally and inline on memory-limited hosts)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.idempotency import ReviewIdempotencyLock
from app.db.sync_session import get_sync_session_factory
from app.models.orm.pull_request import PullRequestRecord
from app.models.schemas.code_review import CodeReviewResult
from app.services.github_client import GitHubReviewPublisher, GitHubService, GitHubServiceError
from app.services.llm_reviewer import LLMReviewer, LLMReviewerError
from app.services.review_persistence import (
    filter_comments_by_rules,
    get_review_rules,
    mark_review_completed,
    mark_review_failed,
    mark_review_pending,
)

logger = logging.getLogger(__name__)


def _persist_diff(
    session_factory: sessionmaker[Session],
    record_id: str,
    diff_content: str,
) -> None:
    with session_factory() as session:
        stmt = select(PullRequestRecord).where(PullRequestRecord.id == uuid.UUID(record_id))
        record = session.execute(stmt).scalar_one_or_none()
        if record is None:
            logger.warning("Pull request record %s not found when persisting diff", record_id)
            return
        record.diff_content = diff_content
        record.diff_fetched_at = datetime.now(UTC)
        session.commit()


def execute_pr_review(
    *,
    record_id: str,
    installation_id: int,
    repository_full_name: str,
    pr_number: int,
    head_sha: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Fetch diff, run LLM review, post GitHub comments, update the database."""
    settings = settings or get_settings()
    lock = ReviewIdempotencyLock(settings)
    github_service = GitHubService(settings)
    llm_reviewer = LLMReviewer(settings)
    publisher = GitHubReviewPublisher(github_service)
    session_factory = get_sync_session_factory()

    with session_factory() as session:
        mark_review_pending(session, record_id)

    try:
        logger.info(
            "Processing PR review: %s#%s @ %s (record=%s)",
            repository_full_name,
            pr_number,
            head_sha[:7],
            record_id,
        )

        raw_diff = github_service.fetch_pull_request_diff(
            installation_id=installation_id,
            repository_full_name=repository_full_name,
            pr_number=pr_number,
        )
        _persist_diff(session_factory, record_id, raw_diff)

        review = llm_reviewer.review_diff(raw_diff)

        with session_factory() as session:
            rules = get_review_rules(session)
            filtered_comments = filter_comments_by_rules(review.comments, rules)
            filtered_review = CodeReviewResult(comments=filtered_comments)

        posted = publisher.post_inline_review_comments(
            installation_id=installation_id,
            repository_full_name=repository_full_name,
            pr_number=pr_number,
            head_sha=head_sha,
            review=filtered_review,
        )

        with session_factory() as session:
            mark_review_completed(
                session,
                record_id,
                filtered_review,
                comments_posted=len(posted),
            )

        lock.mark_completed(repository_full_name, head_sha)
        return {
            "status": "completed",
            "record_id": record_id,
            "comments_generated": len(review.comments),
            "comments_posted": len(posted),
        }
    except (GitHubServiceError, LLMReviewerError, Exception) as exc:
        logger.exception(
            "PR review failed for %s#%s: %s",
            repository_full_name,
            pr_number,
            exc,
        )
        with session_factory() as session:
            mark_review_failed(session, record_id, str(exc))
        lock.release(repository_full_name, head_sha)
        return {"status": "failed", "record_id": record_id, "error": str(exc)}
