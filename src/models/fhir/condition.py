"""Condition FHIR resource model (diagnoses)."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class ClinicalStatus(str, Enum):
    ACTIVE = "active"
    RECURRENCE = "recurrence"
    RELAPSE = "relapse"
    INACTIVE = "inactive"
    REMISSION = "remission"
    RESOLVED = "resolved"


class DiagnosisRecord(BaseModel):
    """Patient diagnosis mapped to ICD-10 and SNOMED CT."""

    id: str
    patient_id: str
    icd10_code: str
    snomed_code: str | None = None
    display_name: str
    clinical_status: ClinicalStatus = ClinicalStatus.ACTIVE
    onset_date: date | None = None
    recorded_date: date = Field(default_factory=date.today)

    def to_fhir_dict(self) -> dict[str, object]:
        resource: dict[str, object] = {
            "resourceType": "Condition",
            "id": self.id,
            "subject": {"reference": f"Patient/{self.patient_id}"},
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": self.clinical_status.value,
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": self.icd10_code,
                        "display": self.display_name,
                    }
                ]
            },
            "recordedDate": self.recorded_date.isoformat(),
        }
        if self.snomed_code:
            resource["code"]["coding"].append(  # type: ignore[index]
                {
                    "system": "http://snomed.info/sct",
                    "code": self.snomed_code,
                }
            )
        if self.onset_date:
            resource["onsetDateTime"] = self.onset_date.isoformat()
        return resource
