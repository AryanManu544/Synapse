import hashlib
import hmac

SIGNATURE_PREFIX = "sha256="


def verify_github_webhook_signature(
    payload_body: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """
    Validate GitHub's X-Hub-Signature-256 header using HMAC SHA-256.

    See: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
    """
    if not secret or not signature_header:
        return False

    if not signature_header.startswith(SIGNATURE_PREFIX):
        return False

    received_signature = signature_header.removeprefix(SIGNATURE_PREFIX)
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, received_signature)
