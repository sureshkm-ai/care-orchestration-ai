"""Human review models for clinician worklist."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"
    EXPIRED = "expired"


class ReviewDecision(BaseModel):
    """The clinician's decision on a review task."""

    status: ReviewStatus
    reviewer_id: str
    reasoning: str
    alternative_recommendation: dict[str, Any] | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewTask(BaseModel):
    """A task in the clinician review queue."""

    task_id: str
    workflow_id: str  # Correlation ID of the triggering workflow
    a2a_task_id: str  # A2A task that was paused
    agent_id: str  # Which agent escalated
    escalation_trigger: str  # e.g., "ESI_LEVEL_1", "low_confidence"
    patient_id: str
    agent_recommendation: dict[str, Any]  # What the agent suggested
    clinical_context: dict[str, Any]  # Relevant patient data
    status: ReviewStatus = ReviewStatus.PENDING
    assigned_to: str | None = None
    decision: ReviewDecision | None = None
    override_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    sla_deadline: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(hours=1))

    @property
    def is_overdue(self) -> bool:
        return self.status == ReviewStatus.PENDING and datetime.now(UTC) > self.sla_deadline
