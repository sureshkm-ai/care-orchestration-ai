"""Patient FHIR resource model.

Wraps FHIR R4 Patient with application-specific convenience.
BD-4: R4 wire format, R4B-compatible Python classes.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class ContactInfo(BaseModel):
    phone: str | None = None
    email: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


class PatientSummary(BaseModel):
    """Lightweight patient model for internal use."""

    id: str
    mrn: str  # Medical Record Number
    given_name: str
    family_name: str
    birth_date: date
    gender: Gender = Gender.UNKNOWN
    contact: ContactInfo = Field(default_factory=ContactInfo)
    active: bool = True

    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.family_name}"

    @property
    def age(self) -> int:
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    def to_fhir_dict(self) -> dict[str, object]:
        """Convert to FHIR R4 Patient resource dict."""
        resource: dict[str, object] = {
            "resourceType": "Patient",
            "id": self.id,
            "active": self.active,
            "identifier": [
                {
                    "system": "http://hospital.example/mrn",
                    "value": self.mrn,
                }
            ],
            "name": [
                {
                    "use": "official",
                    "family": self.family_name,
                    "given": [self.given_name],
                }
            ],
            "gender": self.gender.value,
            "birthDate": self.birth_date.isoformat(),
        }
        telecom = []
        if self.contact.phone:
            telecom.append({"system": "phone", "value": self.contact.phone})
        if self.contact.email:
            telecom.append({"system": "email", "value": self.contact.email})
        if telecom:
            resource["telecom"] = telecom
        return resource
