from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

IssueType = Literal["security", "performance", "typing", "logic"]
ReviewStatus = Literal["pending", "reviewed", "failed"]


class ReviewSeverity(StrEnum):
    """Severity level for a code review comment."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ReviewComment(BaseModel):
    """A single review finding tied to a file and line."""

    file_path: str = Field(..., description="Repository-relative path to the file")
    line_number: int = Field(..., ge=1, description="1-based line number in the new file")
    severity: ReviewSeverity
    issue_type: IssueType = Field(
        ...,
        description="Category: security, performance, typing, or logic",
    )
    suggested_fix: str = Field(..., min_length=1, description="Concrete remediation guidance")


class CodeReviewResult(BaseModel):
    """Structured LLM output for an entire pull request diff review."""

    comments: list[ReviewComment] = Field(default_factory=list)
