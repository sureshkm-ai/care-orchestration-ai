"""Observation FHIR resource models (vitals and labs).

Maps vital signs and lab results to LOINC codes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class VitalSigns(BaseModel):
    """Patient vital signs with LOINC code mappings."""

    heart_rate: float | None = None  # LOINC: 8867-4
    blood_pressure_systolic: float | None = None  # LOINC: 8480-6
    blood_pressure_diastolic: float | None = None  # LOINC: 8462-4
    temperature_celsius: float | None = None  # LOINC: 8310-5
    respiratory_rate: float | None = None  # LOINC: 9279-1
    oxygen_saturation: float | None = None  # LOINC: 2708-6
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def loinc_code_for(vital_name: str) -> str | None:
        """Get the LOINC code for a vital sign field name."""
        mapping = {
            "heart_rate": "8867-4",
            "blood_pressure_systolic": "8480-6",
            "blood_pressure_diastolic": "8462-4",
            "temperature_celsius": "8310-5",
            "respiratory_rate": "9279-1",
            "oxygen_saturation": "2708-6",
        }
        return mapping.get(vital_name)


class LabResult(BaseModel):
    """A single lab observation result."""

    id: str
    patient_id: str
    loinc_code: str
    display_name: str
    value: float
    unit: str
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    status: str = "final"  # registered | preliminary | final | amended
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_abnormal(self) -> bool:
        if self.reference_range_low is not None and self.value < self.reference_range_low:
            return True
        return self.reference_range_high is not None and self.value > self.reference_range_high
