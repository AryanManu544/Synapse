"""Persist review outcomes and findings from Celery workers."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm.pull_request import PullRequestRecord
from app.models.orm.review_finding import ReviewFinding
from app.models.orm.review_rules import ReviewRuleConfig
from app.models.schemas.code_review import CodeReviewResult, ReviewComment

logger = logging.getLogger(__name__)


def get_review_rules(session: Session) -> ReviewRuleConfig:
    config = session.get(ReviewRuleConfig, 1)
    if config is None:
        config = ReviewRuleConfig(id=1)
        session.add(config)
        session.commit()
        session.refresh(config)
    return config


def filter_comments_by_rules(
    comments: list[ReviewComment],
    rules: ReviewRuleConfig,
) -> list[ReviewComment]:
    """Keep only comments whose issue type is enabled in rule configuration."""
    allowed: set[str] = set()
    if rules.focus_security:
        allowed.add("security")
    if rules.focus_performance:
        allowed.add("performance")
    if rules.focus_strict_typing:
        allowed.add("typing")
    if rules.focus_logic:
        allowed.add("logic")
    return [comment for comment in comments if comment.issue_type in allowed]


def mark_review_pending(session: Session, record_id: str) -> None:
    record = _get_record(session, record_id)
    if record is None:
        return
    record.review_status = "pending"
    record.review_error = None
    session.commit()


def mark_review_completed(
    session: Session,
    record_id: str,
    review: CodeReviewResult,
    *,
    comments_posted: int,
) -> None:
    record = _get_record(session, record_id)
    if record is None:
        return

    record.review_status = "reviewed"
    record.ai_comments_count = comments_posted
    record.review_completed_at = datetime.now(UTC)
    record.review_error = None

    for comment in review.comments:
        session.add(
            ReviewFinding(
                pull_request_id=record.id,
                issue_type=comment.issue_type,
                severity=comment.severity.value,
                file_path=comment.file_path,
                line_number=comment.line_number,
            )
        )

    session.commit()
    logger.info("Marked PR %s as reviewed with %d findings", record_id, len(review.comments))


def mark_review_failed(session: Session, record_id: str, error_message: str) -> None:
    record = _get_record(session, record_id)
    if record is None:
        return
    record.review_status = "failed"
    record.review_error = error_message[:2000]
    record.review_completed_at = datetime.now(UTC)
    session.commit()
    logger.warning("Marked PR %s as failed: %s", record_id, error_message)


def _get_record(session: Session, record_id: str) -> PullRequestRecord | None:
    stmt = select(PullRequestRecord).where(PullRequestRecord.id == uuid.UUID(record_id))
    return session.execute(stmt).scalar_one_or_none()
