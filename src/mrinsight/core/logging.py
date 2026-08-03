from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Format application logs as compact JSON objects."""

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        """Return one JSON object per log record."""

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        fields = getattr(record, "event_fields", None)
        if isinstance(fields, dict):
            payload.update(fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(
    *,
    level: str,
) -> None:
    """Configure process logging for API startup."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)


def log_event(
    event: str,
    **fields: object,
) -> None:
    """Emit one structured application event."""

    logging.getLogger("mrinsight").info(
        event,
        extra={"event_fields": fields},
    )
