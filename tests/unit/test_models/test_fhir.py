"""Tests for FHIR domain models."""

from __future__ import annotations

from datetime import date

from src.models.fhir.condition import DiagnosisRecord
from src.models.fhir.observation import LabResult, VitalSigns
from src.models.fhir.patient import ContactInfo, Gender, PatientSummary


class TestPatientSummary:
    def test_create_patient(self) -> None:
        patient = PatientSummary(
            id="P001",
            mrn="MRN12345",
            given_name="John",
            family_name="Doe",
            birth_date=date(1980, 5, 15),
            gender=Gender.MALE,
        )
        assert patient.full_name == "John Doe"
        assert patient.age > 0

    def test_to_fhir_dict(self) -> None:
        patient = PatientSummary(
            id="P001",
            mrn="MRN12345",
            given_name="Jane",
            family_name="Smith",
            birth_date=date(1990, 1, 1),
            gender=Gender.FEMALE,
            contact=ContactInfo(phone="555-0100", email="jane@example.com"),
        )
        fhir = patient.to_fhir_dict()
        assert fhir["resourceType"] == "Patient"
        assert fhir["id"] == "P001"
        assert fhir["gender"] == "female"
        assert len(fhir["telecom"]) == 2  # type: ignore[arg-type]


class TestVitalSigns:
    def test_create_vitals(self) -> None:
        vitals = VitalSigns(
            heart_rate=72,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            temperature_celsius=37.0,
            oxygen_saturation=98,
        )
        assert vitals.heart_rate == 72

    def test_loinc_mapping(self) -> None:
        assert VitalSigns.loinc_code_for("heart_rate") == "8867-4"
        assert VitalSigns.loinc_code_for("unknown") is None


class TestLabResult:
    def test_abnormal_high(self) -> None:
        lab = LabResult(
            id="L001",
            patient_id="P001",
            loinc_code="2339-0",
            display_name="Glucose",
            value=250,
            unit="mg/dL",
            reference_range_high=100,
        )
        assert lab.is_abnormal is True

    def test_normal(self) -> None:
        lab = LabResult(
            id="L002",
            patient_id="P001",
            loinc_code="2339-0",
            display_name="Glucose",
            value=90,
            unit="mg/dL",
            reference_range_low=70,
            reference_range_high=100,
        )
        assert lab.is_abnormal is False


class TestDiagnosisRecord:
    def test_to_fhir_dict(self) -> None:
        dx = DiagnosisRecord(
            id="D001",
            patient_id="P001",
            icd10_code="I10",
            snomed_code="38341003",
            display_name="Essential hypertension",
        )
        fhir = dx.to_fhir_dict()
        assert fhir["resourceType"] == "Condition"
        assert len(fhir["code"]["coding"]) == 2  # type: ignore[index,arg-type]
