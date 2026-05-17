from pathlib import Path

from github import Auth, Github
from github.GithubException import GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from app.core.config import Settings


class GitHubServiceError(Exception):
    """Raised when GitHub API operations fail."""


class GitHubService:
    """GitHub App client for repository and pull request operations."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _load_private_key(self) -> str:
        if self._settings.github_app_private_key:
            return self._settings.github_app_private_key.replace("\\n", "\n")

        if not self._settings.github_app_private_key_path:
            raise GitHubServiceError("GitHub App private key is not configured.")

        key_path = Path(self._settings.github_app_private_key_path)
        if not key_path.is_file():
            raise GitHubServiceError(f"GitHub App private key not found: {key_path}")

        return key_path.read_text(encoding="utf-8")

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
