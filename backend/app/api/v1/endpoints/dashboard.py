from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import DbSession
from app.models.schemas.dashboard import (
    IssueTypeAnalyticsResponse,
    PullRequestListResponse,
    ReviewRulesResponse,
    ReviewRulesUpdate,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_dashboard = DashboardService()


@router.get("/pull-requests", response_model=PullRequestListResponse)
async def list_pull_requests(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PullRequestListResponse:
    """List recent pull requests with review status and AI comment counts."""
    return await _dashboard.list_pull_requests(session, limit=limit, offset=offset)


@router.get("/rules", response_model=ReviewRulesResponse)
async def get_review_rules(session: DbSession) -> ReviewRulesResponse:
    """Return the current AI review focus configuration."""
    return await _dashboard.get_rules(session)


@router.put("/rules", response_model=ReviewRulesResponse)
async def update_review_rules(
    session: DbSession,
    payload: ReviewRulesUpdate,
) -> ReviewRulesResponse:
    """Update which issue categories the AI reviewer should prioritize."""
    return await _dashboard.update_rules(session, payload)


@router.get("/analytics/issue-types", response_model=IssueTypeAnalyticsResponse)
async def get_issue_type_analytics(
    session: DbSession,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> IssueTypeAnalyticsResponse:
    """Aggregate AI findings by issue type over the requested period."""
    return await _dashboard.get_issue_type_analytics(session, days=days)
