"""Terminology service -- normalize, validate, and translate clinical codes.

Not just lookup files: a service boundary that handles normalization,
value set validation, versioning, and deprecated code handling.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.errors import InvalidTerminologyCodeError
from src.core.terminology.models import CodedConcept, CodingSystem, ValidationResult

# In-memory terminology registries loaded from data files
_registries: dict[CodingSystem, dict[str, CodedConcept]] = {}
_loaded = False


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "terminology"


def load_terminologies() -> None:
    """Load terminology data files into memory."""
    global _loaded
    if _loaded:
        return

    data_dir = _data_dir()
    file_map: dict[CodingSystem, str] = {
        CodingSystem.ICD10: "icd10_common.json",
        CodingSystem.SNOMED: "snomed_symptoms.json",
        CodingSystem.RXNORM: "rxnorm_medications.json",
        CodingSystem.LOINC: "loinc_observations.json",
    }

    for system, filename in file_map.items():
        filepath = data_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
            _registries[system] = {
                entry["code"]: CodedConcept(
                    system=system,
                    code=entry["code"],
                    display=entry["display"],
                    is_active=entry.get("is_active", True),
                )
                for entry in data
            }
        else:
            _registries[system] = {}

    _loaded = True


def validate(system: CodingSystem, code: str) -> ValidationResult:
    """Validate a code against its coding system.

    Returns ValidationResult with validity, deprecation status,
    and suggested replacement if applicable.
    """
    load_terminologies()
    registry = _registries.get(system, {})
    concept = registry.get(code)

    if concept is None:
        # Try to find a close match for suggestion
        suggestion = _find_suggestion(registry, code)
        return ValidationResult(
            valid=False,
            code=code,
            system=system,
            message=f"Code '{code}' not found in {system.value}",
            suggested_replacement=suggestion,
        )

    if not concept.is_active:
        return ValidationResult(
            valid=False,
            code=code,
            system=system,
            display=concept.display,
            is_deprecated=True,
            message=f"Code '{code}' is deprecated/inactive in {system.value}",
        )

    return ValidationResult(
        valid=True,
        code=code,
        system=system,
        display=concept.display,
    )


def validate_or_raise(system: CodingSystem, code: str) -> CodedConcept:
    """Validate a code and raise InvalidTerminologyCodeError if invalid."""
    result = validate(system, code)
    if not result.valid:
        raise InvalidTerminologyCodeError(
            system=system.value,
            code=code,
            suggestion=result.suggested_replacement,
        )
    return CodedConcept(
        system=system,
        code=code,
        display=result.display or "",
        is_active=not result.is_deprecated,
    )


def get_display(system: CodingSystem, code: str) -> str | None:
    """Get human-readable display name for a code."""
    load_terminologies()
    concept = _registries.get(system, {}).get(code)
    return concept.display if concept else None


def normalize(system: CodingSystem, code: str) -> str:
    """Normalize a code (strip whitespace, uppercase where appropriate)."""
    normalized = code.strip()
    if system == CodingSystem.ICD10:
        normalized = normalized.upper()
    return normalized


def _find_suggestion(registry: dict[str, CodedConcept], code: str) -> str | None:
    """Find the closest matching code for a suggestion."""
    code_upper = code.upper()
    for existing_code in registry:
        if existing_code.startswith(code_upper[:3]):
            return existing_code
    return None


def clear_registries() -> None:
    """Clear loaded terminology data (for testing)."""
    global _loaded
    _registries.clear()
    _loaded = False
