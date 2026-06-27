import json

import pytest

from app.core.config import Settings


def test_cors_origins_from_plain_env_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://synapse-mauve-pi.vercel.app")
    settings = Settings()
    assert settings.cors_origins == ["https://synapse-mauve-pi.vercel.app"]


def test_cors_origins_from_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://a.vercel.app, https://b.vercel.app",
    )
    settings = Settings()
    assert settings.cors_origins == ["https://a.vercel.app", "https://b.vercel.app"]


def test_cors_origins_from_json_array(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", json.dumps(["https://a.vercel.app"]))
    settings = Settings()
    assert settings.cors_origins == ["https://a.vercel.app"]
