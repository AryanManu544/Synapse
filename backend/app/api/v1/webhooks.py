import json
import logging
from typing import Annotated

import redis
from celery.exceptions import CeleryError
from fastapi import APIRouter, Header, HTTPException, Request, status
from kombu.exceptions import OperationalError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.deps import SettingsDep, get_session_factory
from app.core.idempotency import ReviewIdempotencyLock
from app.core.security import verify_github_webhook_signature
from app.models.schemas.github_webhook import (
    GitHubPullRequestWebhookEvent,
    GitHubWebhookEventLog,
    PullRequestWebhookAction,
)
from app.models.schemas.webhook import WebhookAcceptedResponse
from app.services.github_service import GitHubService
from app.services.pull_request_service import PullRequestService
from app.tasks.review_tasks import process_pr_review

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

SUPPORTED_PULL_REQUEST_ACTIONS: frozenset[PullRequestWebhookAction] = frozenset(
    {"opened", "synchronize"}
)


def _get_pull_request_service(settings: Settings) -> PullRequestService:
    return PullRequestService(github_service=GitHubService(settings))


@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WebhookAcceptedResponse,
)
async def github_webhook(
    request: Request,
    settings: SettingsDep,
    x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    x_github_event: Annotated[str | None, Header(alias="X-GitHub-Event")] = None,
    x_github_delivery: Annotated[str | None, Header(alias="X-GitHub-Delivery")] = None,
) -> WebhookAcceptedResponse:
    """
    Ingest GitHub App webhook deliveries.

    Verifies HMAC SHA-256, persists pull_request metadata, and enqueues a Celery
    task for background LLM review.
    """
    payload_body = await request.body()

    if not verify_github_webhook_signature(
        payload_body,
        x_hub_signature_256,
        settings.github_webhook_secret,
    ):
        logger.warning(
            "Rejected GitHub webhook: invalid signature (delivery=%s)",
            x_github_delivery,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        payload_dict = json.loads(payload_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    event_log = GitHubWebhookEventLog.model_validate(payload_dict)
    logger.info(
        "GitHub webhook received: event=%s action=%s delivery=%s repo=%s",
        x_github_event,
        event_log.action,
        x_github_delivery,
        event_log.repository.full_name if event_log.repository else None,
        extra={
            "github_event": x_github_event,
            "github_delivery": x_github_delivery,
            "github_action": event_log.action,
        },
    )

    if x_github_event != "pull_request":
        return WebhookAcceptedResponse(
            message=f"Event '{x_github_event}' acknowledged; no pull request processing required",
        )

    action = event_log.action
    if action not in SUPPORTED_PULL_REQUEST_ACTIONS:
        return WebhookAcceptedResponse(
            message=f"Pull request action '{action}' acknowledged; not queued for review",
        )

    try:
        pr_event = GitHubPullRequestWebhookEvent.model_validate(payload_dict)
    except ValidationError as exc:
        logger.error("Invalid pull_request webhook payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid pull_request webhook payload",
        ) from exc

    if pr_event.installation is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GitHub App installation id is required",
        )

    head_sha = pr_event.pull_request.head.sha
    try:
        idempotency = ReviewIdempotencyLock(settings)
        if not idempotency.try_acquire(pr_event.repository.full_name, head_sha):
            return WebhookAcceptedResponse(
                message="Duplicate webhook for this commit; review already queued or completed",
                pull_request_id=None,
            )

        pr_service = _get_pull_request_service(settings)
        session_factory: async_sessionmaker[AsyncSession] = get_session_factory()
        async with session_factory() as session:
            record = await pr_service.upsert_from_webhook(
                session,
                event=pr_event,
                delivery_id=x_github_delivery,
                event_type=x_github_event or "pull_request",
            )

        process_pr_review.delay(
            record_id=str(record.id),
            installation_id=pr_event.installation.id,
            repository_full_name=pr_event.repository.full_name,
            pr_number=pr_event.number,
            head_sha=head_sha,
        )
    except redis.RedisError as exc:
        logger.exception(
            "Webhook failed: Redis error (check REDIS_URL uses rediss:// for Upstash): %s",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable; cannot queue review",
        ) from exc
    except (OperationalError, CeleryError) as exc:
        logger.exception(
            "Webhook failed: Celery broker error (check CELERY_BROKER_URL uses rediss://): %s",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue unavailable; cannot enqueue review",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Webhook failed: database error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while saving pull request",
        ) from exc

    logger.info(
        "Enqueued Celery review task: %s#%s action=%s record_id=%s head=%s",
        pr_event.repository.full_name,
        pr_event.number,
        pr_event.action,
        record.id,
        head_sha[:7],
    )

    return WebhookAcceptedResponse(
        message="Pull request accepted for background review",
        pull_request_id=str(record.id),
    )
