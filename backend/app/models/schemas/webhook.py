from pydantic import BaseModel


class WebhookAcceptedResponse(BaseModel):
    """Response returned after a webhook is accepted for processing."""

    status: str = "accepted"
    message: str
    pull_request_id: str | None = None
