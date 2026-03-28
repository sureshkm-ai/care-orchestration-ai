"""Care plan models for coordinated patient care."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class CarePlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on-hold"
    COMPLETED = "completed"
    REVOKED = "revoked"


class CarePlan(BaseModel):
    """A care plan created by the Care Coordinator agent."""

    plan_id: str
    patient_id: str
    status: CarePlanStatus = CarePlanStatus.ACTIVE
    triage_assessment_id: str | None = None
    appointment_id: str | None = None
    recommended_specialty: str = ""
    urgency_level: str = ""
    next_steps: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = ""  # Agent ID
