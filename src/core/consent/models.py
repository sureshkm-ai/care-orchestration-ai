"""Consent models -- scoped by data type and use case (not binary).

Consent is never just yes/no. Each consent record has multiple scopes
defining which data types, uses, and agents are permitted.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConsentStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    DRAFT = "draft"


class ConsentScope(BaseModel):
    """A single scope within a consent record."""

    data_types: list[str]  # ["demographics", "labs", "medications", "conditions"]
    permitted_uses: list[str]  # ["treatment", "care_coordination", "research"]
    permitted_agents: list[str]  # ["triage_agent", "care_coordinator"]
    valid_from: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime | None = None


class ConsentRecord(BaseModel):
    """Patient consent with multiple scopes."""

    consent_id: str  # FHIR Consent resource ID
    patient_id: str
    status: ConsentStatus = ConsentStatus.ACTIVE
    scopes: list[ConsentScope] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    revocation_date: datetime | None = None
    revocation_reason: str | None = None

    def is_active(self) -> bool:
        return self.status == ConsentStatus.ACTIVE

    def permits(
        self,
        data_type: str,
        use: str,
        agent_id: str,
        at_time: datetime | None = None,
    ) -> bool:
        """Check if this consent permits a specific access pattern."""
        if not self.is_active():
            return False

        check_time = at_time or datetime.now(UTC)
        for scope in self.scopes:
            if scope.valid_until and check_time > scope.valid_until:
                continue
            if check_time < scope.valid_from:
                continue
            if (
                data_type in scope.data_types
                and use in scope.permitted_uses
                and (agent_id in scope.permitted_agents or "*" in scope.permitted_agents)
            ):
                return True
        return False


class BreakGlassRecord(BaseModel):
    """Record of emergency break-glass access."""

    access_id: str
    patient_id: str
    accessor: str  # Agent or clinician ID
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed: bool = False
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_outcome: str | None = None  # "justified" | "violation"
