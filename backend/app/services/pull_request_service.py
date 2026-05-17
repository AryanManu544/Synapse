import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.pull_request import PullRequestRecord
from app.models.schemas.github_webhook import GitHubPullRequestWebhookEvent
from app.services.github_service import GitHubService, GitHubServiceError

logger = logging.getLogger(__name__)


class PullRequestService:
    """Persistence and enrichment for pull request webhook events."""

    def __init__(self, github_service: GitHubService) -> None:
        self._github_service = github_service

    async def upsert_from_webhook(
        self,
        session: AsyncSession,
        *,
        event: GitHubPullRequestWebhookEvent,
        delivery_id: str | None,
        event_type: str,
    ) -> PullRequestRecord:
        """Create or update pull request metadata from a webhook payload."""
        pr = event.pull_request
        author_login = pr.user.login if pr.user else None

        stmt = select(PullRequestRecord).where(
            PullRequestRecord.repository_full_name == event.repository.full_name,
            PullRequestRecord.pr_number == event.number,
            PullRequestRecord.head_sha == pr.head.sha,
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            record = PullRequestRecord(
                delivery_id=delivery_id,
                event_type=event_type,
                action=event.action,
                github_pr_id=pr.id,
                pr_number=event.number,
                repository_full_name=event.repository.full_name,
                installation_id=event.installation.id if event.installation else None,
                title=pr.title,
                author_login=author_login,
                head_sha=pr.head.sha,
                base_sha=pr.base.sha,
                head_ref=pr.head.ref,
                base_ref=pr.base.ref,
                html_url=pr.html_url,
                review_status="pending",
                ai_comments_count=0,
            )
            session.add(record)
        else:
            record.delivery_id = delivery_id
            record.event_type = event_type
            record.action = event.action
            record.title = pr.title
            record.author_login = author_login
            record.base_sha = pr.base.sha
            record.base_ref = pr.base.ref
            record.html_url = pr.html_url
            record.diff_content = None
            record.diff_fetched_at = None
            record.review_status = "pending"
            record.ai_comments_count = 0
            record.review_error = None
            record.review_completed_at = None

        await session.commit()
        await session.refresh(record)
        return record

    async def fetch_and_store_diff(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        *,
        installation_id: int,
        repository_full_name: str,
        pr_number: int,
    ) -> None:
        """Fetch PR diff from GitHub and persist it on the record."""
        stmt = select(PullRequestRecord).where(PullRequestRecord.id == record_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            logger.warning("Pull request record %s not found for diff fetch", record_id)
            return

        try:
            diff = self._github_service.fetch_pull_request_diff(
                installation_id=installation_id,
                repository_full_name=repository_full_name,
                pr_number=pr_number,
            )
        except GitHubServiceError:
            logger.exception(
                "Failed to fetch diff for %s#%s",
                repository_full_name,
                pr_number,
            )
            return

        record.diff_content = diff
        record.diff_fetched_at = datetime.now(UTC)
        await session.commit()

        logger.info(
            "Stored PR diff for %s#%s (%d bytes)",
            repository_full_name,
            pr_number,
            len(diff),
        )
