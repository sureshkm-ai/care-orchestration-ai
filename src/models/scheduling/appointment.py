"""Scheduling domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "noshow"


class Provider(BaseModel):
    """Healthcare provider (doctor, specialist)."""

    id: str
    name: str
    specialty: str
    department: str = ""


class TimeSlot(BaseModel):
    """An available appointment time slot."""

    slot_id: str
    provider_id: str
    start_time: datetime
    end_time: datetime
    is_available: bool = True


class Appointment(BaseModel):
    """A scheduled appointment."""

    id: str
    patient_id: str
    provider_id: str
    specialty: str
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    reason: str = ""
    notes: str = ""
    idempotency_key: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)
