import json
import logging

from app.core.logging import JsonLogFormatter, configure_logging


def test_json_log_formatter_outputs_valid_json() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello world",
        args=(),
        exc_info=None,
        func="test_json_log_formatter_outputs_valid_json",
    )
    record.github_event = "pull_request"  # type: ignore[attr-defined]

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "hello world"
    assert payload["github_event"] == "pull_request"
    assert "timestamp" in payload


def test_configure_logging_json_mode() -> None:
    configure_logging(debug=False, log_format="json")
    logger = logging.getLogger("synapse.test")
    assert logger.getEffectiveLevel() == logging.INFO
