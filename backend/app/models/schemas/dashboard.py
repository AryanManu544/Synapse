from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.schemas.code_review import ReviewStatus


class PullRequestSummary(BaseModel):
    id: UUID
    repository_full_name: str
    pr_number: int
    title: str
    author_login: str | None
    head_ref: str
    review_status: ReviewStatus
    ai_comments_count: int
    html_url: str | None
    created_at: datetime
    review_completed_at: datetime | None


class PullRequestListResponse(BaseModel):
    items: list[PullRequestSummary]
    total: int


class ReviewRulesResponse(BaseModel):
    focus_security: bool
    focus_performance: bool
    focus_strict_typing: bool
    focus_logic: bool
    updated_at: datetime | None = None


class ReviewRulesUpdate(BaseModel):
    focus_security: bool
    focus_performance: bool
    focus_strict_typing: bool
    focus_logic: bool


class IssueTypeAnalyticsItem(BaseModel):
    issue_type: str
    label: str
    count: int


class IssueTypeAnalyticsResponse(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    items: list[IssueTypeAnalyticsItem]
