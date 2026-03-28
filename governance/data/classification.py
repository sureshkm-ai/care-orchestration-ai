"""Data classification tags for healthcare data governance.

Applied to every data access to track sensitivity level.
"""

from __future__ import annotations

from enum import Enum


class DataClassification(str, Enum):
    PHI = "phi"  # Protected Health Information - encrypted, audited, consent-required
    PII = "pii"  # Personally Identifiable - encrypted, audited
    CLINICAL = "clinical"  # De-identified clinical data - audited
    OPERATIONAL = "operational"  # Scheduling, notifications - standard logging
    PUBLIC = "public"  # Drug info, clinical guidelines - no restrictions


# FHIR resource type -> default classification
RESOURCE_CLASSIFICATION: dict[str, DataClassification] = {
    "Patient": DataClassification.PHI,
    "Observation": DataClassification.PHI,
    "Condition": DataClassification.PHI,
    "MedicationRequest": DataClassification.PHI,
    "Encounter": DataClassification.PHI,
    "AllergyIntolerance": DataClassification.PHI,
    "Appointment": DataClassification.OPERATIONAL,
    "Schedule": DataClassification.OPERATIONAL,
    "Slot": DataClassification.OPERATIONAL,
    "Practitioner": DataClassification.OPERATIONAL,
    "Medication": DataClassification.PUBLIC,
}


def classify_resource(resource_type: str) -> DataClassification:
    """Get the data classification for a FHIR resource type."""
    return RESOURCE_CLASSIFICATION.get(resource_type, DataClassification.OPERATIONAL)


def requires_consent(classification: DataClassification) -> bool:
    """Check if a classification requires patient consent for access."""
    return classification in (DataClassification.PHI, DataClassification.PII)


def requires_encryption(classification: DataClassification) -> bool:
    """Check if a classification requires encryption at rest."""
    return classification in (DataClassification.PHI, DataClassification.PII)


def requires_audit(classification: DataClassification) -> bool:
    """Check if a classification requires audit logging."""
    return classification != DataClassification.PUBLIC
