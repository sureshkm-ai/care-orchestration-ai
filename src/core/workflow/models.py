"""Saga workflow models for multi-agent coordination."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"
    UNKNOWN = "unknown"


class SagaStep(BaseModel):
    """A single step in a saga workflow."""

    step_id: str
    name: str  # e.g., "book_appointment"
    status: StepStatus = StepStatus.PENDING
    idempotency_key: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    timeout_ms: int = 10000  # Caller-owned timeout
    result: dict[str, Any] | None = None
    error: str | None = None
    compensating_action: str = ""  # e.g., "cancel_appointment"
    compensation_status: StepStatus | None = None


class SagaStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    PAUSED = "paused"  # Waiting for human review
    RESUMED = "resumed"


class SagaState(BaseModel):
    """Full state of a saga workflow."""

    workflow_id: str
    workflow_name: str  # e.g., "triage_and_route"
    status: SagaStatus = SagaStatus.RUNNING
    correlation_id: str = ""
    patient_id: str | None = None
    steps: list[SagaStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    paused_at_step: str | None = None  # Step ID where paused for human review
    review_task_id: str | None = None

    def current_step(self) -> SagaStep | None:
        """Get the current step (first non-completed step)."""
        for step in self.steps:
            if step.status in (StepStatus.PENDING, StepStatus.RUNNING):
                return step
        return None

    def completed_steps(self) -> list[SagaStep]:
        """Get completed steps (for compensation in reverse order)."""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]
