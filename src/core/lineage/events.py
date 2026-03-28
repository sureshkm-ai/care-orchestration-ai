"""OpenLineage-based healthcare lineage event models.

Every MCP tool call and A2A message emits a HealthcareLineageEvent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RunState(str, Enum):
    START = "START"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"
    ABORT = "ABORT"


class DatasetRef(BaseModel):
    """Reference to a data asset (input or output)."""

    namespace: str  # e.g., "fhir", "scheduling"
    name: str  # e.g., "Patient/P001", "Appointment/A001"


class HealthcareLineageEvent(BaseModel):
    """OpenLineage-compatible event with healthcare-specific facets."""

    # OpenLineage core
    run_id: str
    parent_run_id: str | None = None
    job_namespace: str  # Agent name (e.g., "triage_agent")
    job_name: str  # Operation (e.g., "assess_patient_urgency")
    event_type: RunState
    event_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    inputs: list[DatasetRef] = Field(default_factory=list)
    outputs: list[DatasetRef] = Field(default_factory=list)

    # Healthcare-specific facets
    correlation_id: str = ""
    agent_id: str = ""
    patient_id: str | None = None
    consent_reference: str | None = None
    data_classification: str = "operational"
    mcp_tool_name: str | None = None
    a2a_task_id: str | None = None
    workflow_id: str | None = None
    duration_ms: float | None = None
    error_message: str | None = None
