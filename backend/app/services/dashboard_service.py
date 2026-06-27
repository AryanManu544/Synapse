from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.pull_request import PullRequestRecord
from app.models.orm.review_finding import ReviewFinding
from app.models.orm.review_rules import ReviewRuleConfig
from app.models.schemas.dashboard import (
    IssueTypeAnalyticsItem,
    IssueTypeAnalyticsResponse,
    PullRequestListResponse,
    PullRequestSummary,
    ReviewRulesResponse,
    ReviewRulesUpdate,
)

ISSUE_TYPE_LABELS: dict[str, str] = {
    "security": "Security",
    "performance": "Performance",
    "typing": "Strict Typing",
    "logic": "Logic & Correctness",
}


class DashboardService:
    """Read/write operations for the engineering manager dashboard."""

    async def list_pull_requests(
        self,
        session: AsyncSession,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> PullRequestListResponse:
        count_stmt = select(func.count()).select_from(PullRequestRecord)
        total = int((await session.execute(count_stmt)).scalar_one())

        stmt = (
            select(PullRequestRecord)
            .order_by(PullRequestRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        records = result.scalars().all()

        items = [
            PullRequestSummary(
                id=record.id,
                repository_full_name=record.repository_full_name,
                pr_number=record.pr_number,
                title=record.title,
                author_login=record.author_login,
                head_ref=record.head_ref,
                review_status=record.review_status,
                ai_comments_count=record.ai_comments_count,
                html_url=record.html_url,
                created_at=record.created_at,
                review_completed_at=record.review_completed_at,
            )
            for record in records
        ]
        return PullRequestListResponse(items=items, total=total)

    async def get_rules(self, session: AsyncSession) -> ReviewRulesResponse:
        config = await self._get_or_create_rules(session)
        return ReviewRulesResponse(
            focus_security=config.focus_security,
            focus_performance=config.focus_performance,
            focus_strict_typing=config.focus_strict_typing,
            focus_logic=config.focus_logic,
            updated_at=config.updated_at,
        )

    async def update_rules(
        self,
        session: AsyncSession,
        payload: ReviewRulesUpdate,
    ) -> ReviewRulesResponse:
        config = await self._get_or_create_rules(session)
        config.focus_security = payload.focus_security
        config.focus_performance = payload.focus_performance
        config.focus_strict_typing = payload.focus_strict_typing
        config.focus_logic = payload.focus_logic
        config.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(config)
        return await self.get_rules(session)

    async def get_issue_type_analytics(
        self,
        session: AsyncSession,
        *,
        days: int = 30,
    ) -> IssueTypeAnalyticsResponse:
        since = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(ReviewFinding.issue_type, func.count(ReviewFinding.id))
            .where(ReviewFinding.created_at >= since)
            .group_by(ReviewFinding.issue_type)
            .order_by(func.count(ReviewFinding.id).desc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        items = [
            IssueTypeAnalyticsItem(
                issue_type=issue_type,
                label=ISSUE_TYPE_LABELS.get(issue_type, issue_type.title()),
                count=count,
            )
            for issue_type, count in rows
        ]

        for key, label in ISSUE_TYPE_LABELS.items():
            if not any(item.issue_type == key for item in items):
                items.append(IssueTypeAnalyticsItem(issue_type=key, label=label, count=0))

        items.sort(key=lambda item: item.count, reverse=True)
        return IssueTypeAnalyticsResponse(days=days, items=items)

    async def _get_or_create_rules(self, session: AsyncSession) -> ReviewRuleConfig:
        config = await session.get(ReviewRuleConfig, 1)
        if config is None:
            config = ReviewRuleConfig(id=1)
            session.add(config)
            await session.commit()
            await session.refresh(config)
        return config


async def seed_default_rules(session: AsyncSession) -> None:
    """Ensure default review rule configuration exists."""
    existing = await session.get(ReviewRuleConfig, 1)
    if existing is None:
        session.add(ReviewRuleConfig(id=1))
        await session.commit()
