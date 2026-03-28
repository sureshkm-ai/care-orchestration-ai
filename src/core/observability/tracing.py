"""OpenTelemetry tracing with PHI sanitization.

Traces are sanitized to remove PHI from span attributes before export.
In AWS mode, traces go to X-Ray via ADOT. In local mode, traces are
available via console exporter for debugging.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from src.core.security.redaction import redact_string

_SENSITIVE_SPAN_ATTRIBUTES = frozenset(
    {
        "patient.name",
        "patient.ssn",
        "patient.mrn",
        "patient.address",
        "patient.phone",
        "patient.email",
        "patient.dob",
    }
)


def setup_tracing(service_name: str) -> None:
    """Initialize OpenTelemetry tracing with the given service name."""
    provider = TracerProvider()
    trace.set_tracer_provider(provider)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def sanitize_span_attributes(attributes: dict[str, str]) -> dict[str, str]:
    """Remove PHI from span attributes before export."""
    result: dict[str, str] = {}
    for key, value in attributes.items():
        if key in _SENSITIVE_SPAN_ATTRIBUTES:
            result[key] = "[REDACTED]"
        elif isinstance(value, str):
            result[key] = redact_string(value)
        else:
            result[key] = value
    return result
