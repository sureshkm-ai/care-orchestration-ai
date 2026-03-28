"""Escalation policies defining when agents must defer to humans."""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel


class EscalationPolicy(BaseModel):
    """Defines escalation behavior for a trigger type."""

    trigger: str
    description: str
    sla_timeout: timedelta
    auto_escalate_to: str  # Role to auto-escalate to if SLA breached
    severity: str  # "critical" | "high" | "medium"


# Predefined escalation policies
ESCALATION_POLICIES: dict[str, EscalationPolicy] = {
    "ESI_LEVEL_1": EscalationPolicy(
        trigger="ESI_LEVEL_1",
        description="Immediate life-threatening condition requiring physician review",
        sla_timeout=timedelta(minutes=5),
        auto_escalate_to="attending_physician",
        severity="critical",
    ),
    "ESI_LEVEL_2": EscalationPolicy(
        trigger="ESI_LEVEL_2",
        description="High-risk condition requiring urgent physician review",
        sla_timeout=timedelta(minutes=15),
        auto_escalate_to="attending_physician",
        severity="high",
    ),
    "LOW_CONFIDENCE": EscalationPolicy(
        trigger="LOW_CONFIDENCE",
        description="Agent confidence below threshold, needs clinician validation",
        sla_timeout=timedelta(hours=1),
        auto_escalate_to="charge_nurse",
        severity="medium",
    ),
    "DRUG_CONTRAINDICATION": EscalationPolicy(
        trigger="DRUG_CONTRAINDICATION",
        description="Contraindicated drug interaction detected",
        sla_timeout=timedelta(minutes=30),
        auto_escalate_to="pharmacist",
        severity="high",
    ),
}


def get_escalation_policy(trigger: str) -> EscalationPolicy | None:
    """Get the escalation policy for a given trigger."""
    return ESCALATION_POLICIES.get(trigger)


def get_sla_timeout(trigger: str) -> timedelta:
    """Get the SLA timeout for a trigger. Defaults to 1 hour."""
    policy = ESCALATION_POLICIES.get(trigger)
    return policy.sla_timeout if policy else timedelta(hours=1)
