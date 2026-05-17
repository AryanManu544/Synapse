import hashlib
import hmac

from app.core.security import verify_github_webhook_signature


def test_verify_github_webhook_signature_valid() -> None:
    secret = "test-secret"
    body = b'{"action":"opened"}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    header = f"sha256={digest}"

    assert verify_github_webhook_signature(body, header, secret) is True


def test_verify_github_webhook_signature_invalid() -> None:
    body = b'{"action":"opened"}'
    header = "sha256=deadbeef"

    assert verify_github_webhook_signature(body, header, "test-secret") is False


def test_verify_github_webhook_signature_missing_header() -> None:
    assert verify_github_webhook_signature(b"{}", None, "test-secret") is False
