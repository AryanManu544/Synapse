import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.orm.base import Base
from app.models.schemas.code_review import ReviewStatus


class PullRequestRecord(Base):
    """Persisted pull request metadata from GitHub webhooks."""

    __tablename__ = "pull_requests"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('pending', 'reviewed', 'failed')",
            name="ck_pull_requests_review_status",
        ),
        UniqueConstraint(
            "repository_full_name",
            "pr_number",
            "head_sha",
            name="uq_pull_requests_repo_number_head",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    delivery_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)

    github_pr_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    repository_full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    installation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    author_login: Mapped[str | None] = mapped_column(String(255), nullable=True)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    head_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    base_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    html_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    diff_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review_status: Mapped[ReviewStatus] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    ai_comments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
