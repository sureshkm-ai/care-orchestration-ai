"""Tests for terminology service."""

from __future__ import annotations

import pytest

from src.core.errors import InvalidTerminologyCodeError
from src.core.terminology.models import CodingSystem
from src.core.terminology.service import (
    get_display,
    normalize,
    validate,
    validate_or_raise,
)


class TestTerminologyValidation:
    def test_valid_icd10_code(self) -> None:
        result = validate(CodingSystem.ICD10, "I10")
        assert result.valid is True
        assert result.display == "Essential (primary) hypertension"

    def test_invalid_icd10_code(self) -> None:
        result = validate(CodingSystem.ICD10, "ZZZZ")
        assert result.valid is False

    def test_valid_snomed_code(self) -> None:
        result = validate(CodingSystem.SNOMED, "29857009")
        assert result.valid is True
        assert "Chest pain" in (result.display or "")

    def test_valid_loinc_code(self) -> None:
        result = validate(CodingSystem.LOINC, "8867-4")
        assert result.valid is True
        assert "Heart rate" in (result.display or "")

    def test_validate_or_raise_valid(self) -> None:
        concept = validate_or_raise(CodingSystem.ICD10, "I10")
        assert concept.code == "I10"

    def test_validate_or_raise_invalid(self) -> None:
        with pytest.raises(InvalidTerminologyCodeError):
            validate_or_raise(CodingSystem.ICD10, "INVALID")


class TestTerminologyNormalization:
    def test_normalize_icd10(self) -> None:
        assert normalize(CodingSystem.ICD10, " i10 ") == "I10"

    def test_normalize_snomed(self) -> None:
        assert normalize(CodingSystem.SNOMED, " 29857009 ") == "29857009"


class TestTerminologyDisplay:
    def test_get_display_existing(self) -> None:
        display = get_display(CodingSystem.RXNORM, "197361")
        assert display is not None
        assert "Lisinopril" in display

    def test_get_display_missing(self) -> None:
        display = get_display(CodingSystem.RXNORM, "999999999")
        assert display is None
