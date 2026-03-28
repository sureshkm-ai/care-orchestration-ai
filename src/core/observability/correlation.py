"""Correlation ID propagation for distributed tracing across agents.

Uses contextvars for async-safe state. The correlation ID is generated
when an A2A request arrives and propagated to all MCP tool calls and
audit log entries.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def new_correlation_id() -> str:
    """Generate and set a new correlation ID."""
    cid = str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID (e.g., from an incoming A2A request header)."""
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    """Get the current correlation ID. Returns empty string if not set."""
    return _correlation_id.get()


def ensure_correlation_id() -> str:
    """Get existing or create new correlation ID."""
    cid = _correlation_id.get()
    if not cid:
        cid = new_correlation_id()
    return cid
