import base64

import pytest

from app.core.config import Settings
from app.core.github_key import GitHubKeyError, load_github_app_private_key

_SAMPLE_PEM = """-----BEGIN RSA PRIVATE KEY-----
abc
-----END RSA PRIVATE KEY-----"""


def test_load_private_key_from_base64() -> None:
    settings = Settings(
        github_app_private_key_b64=base64.b64encode(_SAMPLE_PEM.encode()).decode(),
    )
    assert load_github_app_private_key(settings) == _SAMPLE_PEM


def test_load_private_key_rejects_truncated_inline() -> None:
    settings = Settings(github_app_private_key="-----BEGIN RSA PRIVATE KEY-----\\n")
    with pytest.raises(GitHubKeyError, match="truncated"):
        load_github_app_private_key(settings)
