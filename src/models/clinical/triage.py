"""Triage assessment models using ESI (Emergency Severity Index)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class UrgencyLevel(str, Enum):
    """Emergency Severity Index levels."""

    EMERGENCY = "emergency"  # ESI Level 1: immediate life-saving intervention
    URGENT = "urgent"  # ESI Level 2: high risk, confused/lethargic, severe pain
    LESS_URGENT = "less_urgent"  # ESI Level 3: multiple resources needed
    NON_URGENT = "non_urgent"  # ESI Level 4: one resource needed
    ROUTINE = "routine"  # ESI Level 5: no resources needed

    @property
    def esi_level(self) -> int:
        return {
            UrgencyLevel.EMERGENCY: 1,
            UrgencyLevel.URGENT: 2,
            UrgencyLevel.LESS_URGENT: 3,
            UrgencyLevel.NON_URGENT: 4,
            UrgencyLevel.ROUTINE: 5,
        }[self]

    @property
    def requires_human_review(self) -> bool:
        """ESI Level 1-2 always require human review."""
        return self.esi_level <= 2


class Symptom(BaseModel):
    name: str
    snomed_code: str | None = None
    severity: int = Field(ge=1, le=10, default=5)
    duration_hours: float | None = None
    onset: str | None = None  # "sudden" | "gradual"


class SymptomReport(BaseModel):
    """Patient symptom intake report."""

    patient_id: str
    chief_complaint: str
    symptoms: list[Symptom] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TriageAssessment(BaseModel):
    """Result of triage assessment."""

    assessment_id: str
    patient_id: str
    symptoms: list[str]
    urgency_level: UrgencyLevel
    recommended_specialty: str
    reasoning: str
    icd10_suggestions: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def requires_escalation(self) -> bool:
        """Check if this assessment should be escalated to human review."""
        return self.urgency_level.requires_human_review or self.confidence_score < 0.7
