"""Clinical safety guardrails for AI agent decisions.

Enforced in agent logic to prevent unsafe clinical actions.
"""

from __future__ import annotations

from src.core.errors import EscalationRequiredError
from src.models.clinical.triage import TriageAssessment, UrgencyLevel
from src.models.fhir.observation import VitalSigns

# Critical vital sign thresholds that require immediate escalation
CRITICAL_VITALS = {
    "heart_rate_high": 150.0,
    "heart_rate_low": 40.0,
    "systolic_bp_high": 200.0,
    "systolic_bp_low": 80.0,
    "temperature_high": 40.5,  # Celsius
    "oxygen_saturation_low": 88.0,
    "respiratory_rate_high": 30.0,
}

# Symptoms that always require immediate human review
IMMEDIATE_ESCALATION_SYMPTOMS = frozenset(
    {
        "cardiac_arrest",
        "stroke_symptoms",
        "anaphylaxis",
        "severe_hemorrhage",
        "respiratory_arrest",
        "seizure",
        "loss_of_consciousness",
        "severe_trauma",
    }
)


def check_vital_signs_critical(vitals: VitalSigns) -> list[str]:
    """Check if vital signs indicate a critical condition.

    Returns list of triggered alerts (empty if vitals are within normal range).
    """
    alerts: list[str] = []

    if vitals.heart_rate is not None:
        if vitals.heart_rate >= CRITICAL_VITALS["heart_rate_high"]:
            alerts.append(f"Critical tachycardia: HR {vitals.heart_rate}")
        elif vitals.heart_rate <= CRITICAL_VITALS["heart_rate_low"]:
            alerts.append(f"Critical bradycardia: HR {vitals.heart_rate}")

    if vitals.blood_pressure_systolic is not None:
        if vitals.blood_pressure_systolic >= CRITICAL_VITALS["systolic_bp_high"]:
            alerts.append(f"Hypertensive crisis: SBP {vitals.blood_pressure_systolic}")
        elif vitals.blood_pressure_systolic <= CRITICAL_VITALS["systolic_bp_low"]:
            alerts.append(f"Hypotension: SBP {vitals.blood_pressure_systolic}")

    if (
        vitals.temperature_celsius is not None
        and vitals.temperature_celsius >= CRITICAL_VITALS["temperature_high"]
    ):
        alerts.append(f"Hyperpyrexia: Temp {vitals.temperature_celsius}C")

    if (
        vitals.oxygen_saturation is not None
        and vitals.oxygen_saturation <= CRITICAL_VITALS["oxygen_saturation_low"]
    ):
        alerts.append(f"Critical hypoxemia: SpO2 {vitals.oxygen_saturation}%")

    if (
        vitals.respiratory_rate is not None
        and vitals.respiratory_rate >= CRITICAL_VITALS["respiratory_rate_high"]
    ):
        alerts.append(f"Tachypnea: RR {vitals.respiratory_rate}")

    return alerts


def check_triage_escalation(assessment: TriageAssessment) -> str | None:
    """Check if a triage assessment requires human escalation.

    Returns the escalation trigger string, or None if no escalation needed.
    """
    if assessment.urgency_level == UrgencyLevel.EMERGENCY:
        return "ESI_LEVEL_1"
    if assessment.urgency_level == UrgencyLevel.URGENT:
        return "ESI_LEVEL_2"
    if assessment.confidence_score < 0.7:
        return "LOW_CONFIDENCE"
    return None


def enforce_triage_guardrails(assessment: TriageAssessment, agent_id: str) -> None:
    """Enforce safety guardrails on a triage assessment.

    Raises EscalationRequiredError if human review is needed.
    """
    trigger = check_triage_escalation(assessment)
    if trigger:
        raise EscalationRequiredError(
            trigger=trigger,
            agent_id=agent_id,
            patient_id=assessment.patient_id,
        )
