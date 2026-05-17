from github import Auth, Github
from github.GithubException import GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from app.core.config import Settings
from app.core.github_key import GitHubKeyError, load_github_app_private_key


class GitHubServiceError(Exception):
    """Raised when GitHub API operations fail."""


class GitHubService:
    """GitHub App client for repository and pull request operations."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _load_private_key(self) -> str:
        try:
            return load_github_app_private_key(self._settings)
        except GitHubKeyError as exc:
            raise GitHubServiceError(str(exc)) from exc

    def get_github_client(self, installation_id: int) -> Github:
        """Return an authenticated PyGithub client for a GitHub App installation."""
        if not self._settings.github_app_id:
            raise GitHubServiceError("GITHUB_APP_ID is not configured.")

        private_key = self._load_private_key()
        app_auth = Auth.AppAuth(self._settings.github_app_id, private_key)
        installation_auth = app_auth.get_installation_auth(installation_id)
        return Github(auth=installation_auth)

    def fetch_pull_request_diff(
        self,
        installation_id: int,
        repository_full_name: str,
        pr_number: int,
    ) -> str:
        """Fetch the raw unified diff for a pull request via the GitHub API."""
        github = self.get_github_client(installation_id)
        try:
            repo: Repository = github.get_repo(repository_full_name)
            pull: PullRequest = repo.get_pull(pr_number)
            status, _, diff_body = repo._requester.requestJson(
                "GET",
                pull.url,
                headers={"Accept": "application/vnd.github.v3.diff"},
            )
        except GithubException as exc:
            raise GitHubServiceError(f"GitHub API error: {exc.data}") from exc

        if status >= 400:
            raise GitHubServiceError(f"Failed to fetch PR diff (HTTP {status}).")

        return diff_body
