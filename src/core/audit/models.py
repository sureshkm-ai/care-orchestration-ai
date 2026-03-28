"""HIPAA audit event models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    LOGIN = "login"
    EXPORT = "export"
    ESCALATE = "escalate"
    BREAK_GLASS = "break_glass"


class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class AuditEvent(BaseModel):
    """HIPAA-compliant audit event.

    Captures: who did what, to which resource, for which patient,
    with what outcome, correlated across the workflow.
    """

    event_id: str = Field(default_factory=lambda: "")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str  # Agent ID or user ID
    action: AuditAction
    resource_type: str  # FHIR resource type (Patient, Observation, etc.)
    resource_id: str  # FHIR resource ID
    patient_id: str | None = None
    outcome: AuditOutcome
    correlation_id: str = ""
    consent_reference: str | None = None
    data_classification: str = "operational"
    details: dict[str, str] | None = None
    previous_hash: str = ""  # Hash chain for tamper resistance
    event_hash: str = ""
