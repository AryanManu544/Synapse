import os

# Settings validates required secrets at import time (app.core.config loads on collection).
# setdefault keeps CI-provided values while supplying safe defaults for local pytest runs.
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("GITHUB_APP_ID", "123456")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
