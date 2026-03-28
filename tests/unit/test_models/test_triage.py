"""Tests for triage and clinical models."""

from __future__ import annotations

from src.models.clinical.triage import (
    Symptom,
    SymptomReport,
    TriageAssessment,
    UrgencyLevel,
)


class TestUrgencyLevel:
    def test_esi_levels(self) -> None:
        assert UrgencyLevel.EMERGENCY.esi_level == 1
        assert UrgencyLevel.ROUTINE.esi_level == 5

    def test_requires_human_review(self) -> None:
        assert UrgencyLevel.EMERGENCY.requires_human_review is True
        assert UrgencyLevel.URGENT.requires_human_review is True
        assert UrgencyLevel.LESS_URGENT.requires_human_review is False
        assert UrgencyLevel.ROUTINE.requires_human_review is False


class TestTriageAssessment:
    def test_requires_escalation_esi1(self) -> None:
        assessment = TriageAssessment(
            assessment_id="T001",
            patient_id="P001",
            symptoms=["chest pain"],
            urgency_level=UrgencyLevel.EMERGENCY,
            recommended_specialty="cardiology",
            reasoning="Acute chest pain with cardiac risk factors",
        )
        assert assessment.requires_escalation is True

    def test_no_escalation_routine(self) -> None:
        assessment = TriageAssessment(
            assessment_id="T002",
            patient_id="P002",
            symptoms=["headache"],
            urgency_level=UrgencyLevel.ROUTINE,
            recommended_specialty="general_medicine",
            reasoning="Mild tension headache",
            confidence_score=0.95,
        )
        assert assessment.requires_escalation is False

    def test_low_confidence_triggers_escalation(self) -> None:
        assessment = TriageAssessment(
            assessment_id="T003",
            patient_id="P003",
            symptoms=["unusual rash"],
            urgency_level=UrgencyLevel.NON_URGENT,
            recommended_specialty="dermatology",
            reasoning="Unrecognized symptom pattern",
            confidence_score=0.5,
        )
        assert assessment.requires_escalation is True


class TestSymptomReport:
    def test_create_symptom_report(self) -> None:
        report = SymptomReport(
            patient_id="P001",
            chief_complaint="chest pain",
            symptoms=[
                Symptom(name="chest pain", severity=8),
                Symptom(name="shortness of breath", severity=6),
            ],
        )
        assert len(report.symptoms) == 2
        assert report.symptoms[0].severity == 8
