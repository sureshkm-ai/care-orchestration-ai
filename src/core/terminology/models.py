"""Terminology models for clinical coding systems."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class CodingSystem(str, Enum):
    ICD10 = "http://hl7.org/fhir/sid/icd-10-cm"
    SNOMED = "http://snomed.info/sct"
    RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
    LOINC = "http://loinc.org"


class CodedConcept(BaseModel):
    """A coded clinical concept."""

    system: CodingSystem
    code: str
    display: str
    is_active: bool = True


class ValidationResult(BaseModel):
    """Result of validating a terminology code."""

    valid: bool
    code: str
    system: CodingSystem
    display: str | None = None
    is_deprecated: bool = False
    suggested_replacement: str | None = None
    message: str | None = None
