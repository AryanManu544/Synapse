from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PullRequestWebhookAction = Literal["opened", "synchronize"]


class GitHubUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str
    id: int | None = None


class GitHubRef(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sha: str
    ref: str


class GitHubPullRequestPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    number: int
    title: str
    html_url: str | None = None
    head: GitHubRef
    base: GitHubRef
    user: GitHubUser | None = None


class GitHubRepositoryPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    full_name: str
    name: str
    owner: GitHubUser


class GitHubInstallationPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int


class GitHubPullRequestWebhookEvent(BaseModel):
    """GitHub pull_request webhook payload (opened / synchronize)."""

    model_config = ConfigDict(extra="ignore")

    action: PullRequestWebhookAction
    number: int = Field(..., description="Pull request number in the repository")
    pull_request: GitHubPullRequestPayload
    repository: GitHubRepositoryPayload
    installation: GitHubInstallationPayload | None = None


class GitHubWebhookEventLog(BaseModel):
    """Minimal envelope for logging any validated GitHub webhook delivery."""

    model_config = ConfigDict(extra="ignore")

    action: str | None = None
    zen: str | None = None
    hook_id: int | None = None
    repository: GitHubRepositoryPayload | None = None
    pull_request: GitHubPullRequestPayload | None = None
    installation: GitHubInstallationPayload | None = None
