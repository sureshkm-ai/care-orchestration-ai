"""Lineage context propagation using ContextVar.

Carries lineage metadata (run_id, parent_run_id, correlation_id,
consent_reference, data_classification) across async agent calls.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from pydantic import BaseModel, Field


class LineageContext(BaseModel):
    """Lineage metadata carried through agent operations."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_run_id: str | None = None
    correlation_id: str = ""
    agent_id: str = ""
    patient_id: str | None = None
    consent_reference: str | None = None
    data_classification: str = "operational"
    workflow_id: str | None = None

    def child(self, agent_id: str) -> LineageContext:
        """Create a child context for a downstream agent call."""
        return LineageContext(
            run_id=str(uuid.uuid4()),
            parent_run_id=self.run_id,
            correlation_id=self.correlation_id,
            agent_id=agent_id,
            patient_id=self.patient_id,
            consent_reference=self.consent_reference,
            data_classification=self.data_classification,
            workflow_id=self.workflow_id,
        )

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers for A2A propagation."""
        headers: dict[str, str] = {
            "X-Lineage-Run-ID": self.run_id,
            "X-Lineage-Correlation-ID": self.correlation_id,
            "X-Lineage-Agent-ID": self.agent_id,
        }
        if self.parent_run_id:
            headers["X-Lineage-Parent-Run-ID"] = self.parent_run_id
        if self.patient_id:
            headers["X-Lineage-Patient-ID"] = self.patient_id
        if self.consent_reference:
            headers["X-Lineage-Consent-Ref"] = self.consent_reference
        if self.workflow_id:
            headers["X-Lineage-Workflow-ID"] = self.workflow_id
        return headers

    @classmethod
    def from_headers(cls, headers: dict[str, str], agent_id: str) -> LineageContext:
        """Parse lineage context from incoming A2A request headers."""
        return cls(
            run_id=str(uuid.uuid4()),  # New run for this agent
            parent_run_id=headers.get("X-Lineage-Run-ID"),
            correlation_id=headers.get("X-Lineage-Correlation-ID", ""),
            agent_id=agent_id,
            patient_id=headers.get("X-Lineage-Patient-ID"),
            consent_reference=headers.get("X-Lineage-Consent-Ref"),
            workflow_id=headers.get("X-Lineage-Workflow-ID"),
        )


_lineage_context: ContextVar[LineageContext | None] = ContextVar("lineage_context", default=None)


def set_lineage_context(ctx: LineageContext) -> None:
    _lineage_context.set(ctx)


def get_lineage_context() -> LineageContext | None:
    return _lineage_context.get()


def ensure_lineage_context(agent_id: str = "") -> LineageContext:
    ctx = _lineage_context.get()
    if ctx is None:
        ctx = LineageContext(agent_id=agent_id)
        _lineage_context.set(ctx)
    return ctx
