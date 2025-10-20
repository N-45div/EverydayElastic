from __future__ import annotations

import json
import logging
from logging.config import dictConfig
from typing import Any


class JSONLogFormatter(logging.Formatter):
    """Render log records as JSON compatible with Elastic ingestion."""

    default_fields = {
        "log.level": "levelname",
        "log.logger": "name",
        "message": "message",
        "timestamp": "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - inherited docstring
        payload: dict[str, Any] = {}

        for field_name, record_attr in self.default_fields.items():
            value = self._resolve(record, record_attr)
            if value is not None:
                payload[field_name] = value

        if record.exc_info:
            payload["error.type"] = record.exc_info[0].__name__
            payload["error.message"] = self.formatException(record.exc_info)

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)

        # Include additional custom attributes that are not default LogRecord items
        default_record = logging.makeLogRecord({})
        for key, value in record.__dict__.items():
            if key in default_record.__dict__:
                continue
            if key in payload:
                continue
            payload[key] = value

        return json.dumps(payload, default=str)

    @staticmethod
    def _resolve(record: logging.LogRecord, attribute: str) -> Any:
        if attribute == "message":
            return record.getMessage()
        return getattr(record, attribute, None)


def setup_logging(level: int | str = "INFO") -> None:
    """Configure root logging with JSON output for Elastic observability."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "app.core.logging_config.JSONLogFormatter",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                }
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {
                "handlers": ["stdout"],
                "level": level,
            },
        }
    )
