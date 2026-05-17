import base64
import binascii
from pathlib import Path

from app.core.config import Settings


class GitHubKeyError(Exception):
    """Raised when the GitHub App private key cannot be loaded."""


def load_github_app_private_key(settings: Settings) -> str:
    """Load PEM from base64, inline env, or file path (Render-friendly order)."""
    if settings.github_app_private_key_b64:
        try:
            pem = base64.b64decode(settings.github_app_private_key_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise GitHubKeyError("GITHUB_APP_PRIVATE_KEY_B64 is not valid base64.") from exc
        return pem.decode("utf-8")

    if settings.github_app_private_key:
        key = settings.github_app_private_key.replace("\\n", "\n").strip()
        if "-----END" not in key:
            raise GitHubKeyError(
                "GITHUB_APP_PRIVATE_KEY looks truncated (missing -----END ... -----). "
                "On Render, use GITHUB_APP_PRIVATE_KEY_B64 (one line) or a Secret File + "
                "GITHUB_APP_PRIVATE_KEY_PATH."
            )
        return key

    if settings.github_app_private_key_path:
        key_path = Path(settings.github_app_private_key_path)
        if not key_path.is_file():
            raise GitHubKeyError(f"GitHub App private key not found: {key_path}")
        return key_path.read_text(encoding="utf-8")

    raise GitHubKeyError(
        "GitHub App private key is not configured. Set GITHUB_APP_PRIVATE_KEY_B64, "
        "GITHUB_APP_PRIVATE_KEY, or GITHUB_APP_PRIVATE_KEY_PATH."
    )
