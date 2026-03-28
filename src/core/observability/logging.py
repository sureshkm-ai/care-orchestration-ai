"""Structured JSON logging with PHI redaction.

Uses structlog for JSON-formatted output. All log events pass through
the PHI redaction processor to ensure no raw PHI appears in logs.
Log output goes to stderr (important for MCP stdio compatibility).
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from src.core.observability.correlation import get_correlation_id
from src.core.security.redaction import redact_dict


def _add_correlation_id(
    logger: Any,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Inject the current correlation ID into every log event."""
    cid = get_correlation_id()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def _redact_phi(
    logger: Any,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Redact PHI patterns from log events."""
    return redact_dict(dict(event_dict))


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON output, correlation IDs, and PHI redaction."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_correlation_id,
            _redact_phi,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
