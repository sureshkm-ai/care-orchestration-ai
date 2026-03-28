"""Tests for clinical safety guardrails."""

from __future__ import annotations

import pytest

from governance.clinical.safety_guardrails import (
    check_triage_escalation,
    check_vital_signs_critical,
    enforce_triage_guardrails,
)
from src.core.errors import EscalationRequiredError
from src.models.clinical.triage import TriageAssessment, UrgencyLevel
from src.models.fhir.observation import VitalSigns


class TestVitalSignsGuardrails:
    def test_normal_vitals_no_alerts(self) -> None:
        vitals = VitalSigns(
            heart_rate=72,
            blood_pressure_systolic=120,
            temperature_celsius=37.0,
            oxygen_saturation=98,
        )
        alerts = check_vital_signs_critical(vitals)
        assert len(alerts) == 0

    def test_tachycardia_alert(self) -> None:
        vitals = VitalSigns(heart_rate=160)
        alerts = check_vital_signs_critical(vitals)
        assert any("tachycardia" in a.lower() for a in alerts)

    def test_hypotension_alert(self) -> None:
        vitals = VitalSigns(blood_pressure_systolic=70)
        alerts = check_vital_signs_critical(vitals)
        assert any("hypotension" in a.lower() for a in alerts)

    def test_hypoxemia_alert(self) -> None:
        vitals = VitalSigns(oxygen_saturation=85)
        alerts = check_vital_signs_critical(vitals)
        assert any("hypoxemia" in a.lower() for a in alerts)

    def test_multiple_alerts(self) -> None:
        vitals = VitalSigns(
            heart_rate=160,
            blood_pressure_systolic=70,
            oxygen_saturation=80,
        )
        alerts = check_vital_signs_critical(vitals)
        assert len(alerts) >= 3


class TestTriageEscalation:
    def test_esi1_requires_escalation(self) -> None:
        assessment = TriageAssessment(
            assessment_id="T001",
            patient_id="P001",
            symptoms=["cardiac arrest"],
            urgency_level=UrgencyLevel.EMERGENCY,
            recommended_specialty="emergency",
            reasoning="Cardiac arrest",
        )
        trigger = check_triage_escalation(assessment)
        assert trigger == "ESI_LEVEL_1"

    def test_routine_no_escalation(self) -> None:
        assessment = TriageAssessment(
            assessment_id="T002",
            patient_id="P002",
            symptoms=["mild headache"],
            urgency_level=UrgencyLevel.ROUTINE,
            recommended_specialty="general",
            reasoning="Tension headache",
            confidence_score=0.95,
        )
        trigger = check_triage_escalation(assessment)
        assert trigger is None

    def test_enforce_raises_on_esi1(self) -> None:
        assessment = TriageAssessment(
            assessment_id="T003",
            patient_id="P003",
            symptoms=["stroke symptoms"],
            urgency_level=UrgencyLevel.EMERGENCY,
            recommended_specialty="neurology",
            reasoning="Acute stroke",
        )
        with pytest.raises(EscalationRequiredError, match="ESI_LEVEL_1"):
            enforce_triage_guardrails(assessment, "triage_agent")
