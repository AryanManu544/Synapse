from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, Literal

LogFormat = Literal["json", "text"]


class JsonLogFormatter(logging.Formatter):
    """Emit single-line JSON log records for production observability stacks."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.pathname:
            payload["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        reserved = logging.LogRecord("", 0, "", 0, "", (), None, None).__dict__.keys()
        for key, value in record.__dict__.items():
            if key not in reserved and key not in {"message", "asctime"}:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(
    *,
    debug: bool = False,
    log_format: LogFormat = "json",
) -> None:
    """Configure application-wide logging (JSON for production monitoring)."""
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)

    if log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Align framework loggers with the same handler/format
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "celery"):
        framework_logger = logging.getLogger(logger_name)
        framework_logger.handlers.clear()
        framework_logger.propagate = True
        framework_logger.setLevel(level)

    logging.getLogger(__name__).info(
        "Logging configured",
        extra={"log_format": log_format, "level": logging.getLevelName(level)},
    )
