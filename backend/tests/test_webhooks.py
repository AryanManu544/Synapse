import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_github_webhook_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    get_settings.cache_clear()

    body = json.dumps({"action": "opened"}).encode()
    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": "sha256=invalid",
            "X-GitHub-Event": "pull_request",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401
    get_settings.cache_clear()


def test_github_webhook_accepts_ping_event(monkeypatch) -> None:
    secret = "test-secret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    get_settings.cache_clear()

    body = json.dumps({"zen": "Keep it logically awesome."}).encode()
    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body, secret),
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "delivery-123",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    get_settings.cache_clear()
