"""Domain exception hierarchy for the healthcare platform."""

from __future__ import annotations


class HealthcareError(Exception):
    """Base exception for all healthcare platform errors."""

    def __init__(self, message: str, *, code: str = "HEALTHCARE_ERROR") -> None:
        self.code = code
        super().__init__(message)


# --- Patient errors ---


class PatientNotFoundError(HealthcareError):
    def __init__(self, patient_id: str) -> None:
        super().__init__(f"Patient not found: {patient_id}", code="PATIENT_NOT_FOUND")
        self.patient_id = patient_id


class PatientIdentityConflictError(HealthcareError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="PATIENT_IDENTITY_CONFLICT")


# --- FHIR errors ---


class InvalidFHIRResourceError(HealthcareError):
    def __init__(self, resource_type: str, detail: str) -> None:
        super().__init__(f"Invalid FHIR {resource_type}: {detail}", code="INVALID_FHIR_RESOURCE")
        self.resource_type = resource_type


# --- Clinical errors ---


class TriageError(HealthcareError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="TRIAGE_ERROR")


class EscalationRequiredError(HealthcareError):
    """Raised when a clinical decision requires human review."""

    def __init__(self, trigger: str, *, agent_id: str, patient_id: str) -> None:
        super().__init__(f"Human review required: {trigger}", code="ESCALATION_REQUIRED")
        self.trigger = trigger
        self.agent_id = agent_id
        self.patient_id = patient_id


# --- Pharmacy errors ---


class DrugInteractionError(HealthcareError):
    def __init__(self, drug_a: str, drug_b: str, severity: str) -> None:
        super().__init__(
            f"Drug interaction ({severity}): {drug_a} + {drug_b}",
            code="DRUG_INTERACTION",
        )
        self.drug_a = drug_a
        self.drug_b = drug_b
        self.severity = severity


# --- Scheduling errors ---


class SchedulingConflictError(HealthcareError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="SCHEDULING_CONFLICT")


class AppointmentNotFoundError(HealthcareError):
    def __init__(self, appointment_id: str) -> None:
        super().__init__(f"Appointment not found: {appointment_id}", code="APPOINTMENT_NOT_FOUND")


# --- Authorization errors ---


class AuthorizationError(HealthcareError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="AUTHORIZATION_ERROR")


class ConsentRequiredError(HealthcareError):
    def __init__(self, patient_id: str, data_type: str, use: str) -> None:
        super().__init__(
            f"Consent required for {data_type} ({use}) on patient {patient_id}",
            code="CONSENT_REQUIRED",
        )
        self.patient_id = patient_id
        self.data_type = data_type
        self.use = use


class ConsentDeniedError(HealthcareError):
    def __init__(self, patient_id: str, reason: str) -> None:
        super().__init__(
            f"Consent denied for patient {patient_id}: {reason}",
            code="CONSENT_DENIED",
        )


class BreakGlassAccessError(HealthcareError):
    """Logged when break-glass access is used (not a true error)."""

    def __init__(self, patient_id: str, reason: str, accessor: str) -> None:
        super().__init__(
            f"Break-glass access by {accessor} for patient {patient_id}: {reason}",
            code="BREAK_GLASS_ACCESS",
        )


# --- Audit errors ---


class AuditError(HealthcareError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="AUDIT_ERROR")


# --- Agent communication errors ---


class AgentCommunicationError(HealthcareError):
    def __init__(self, agent_id: str, detail: str) -> None:
        super().__init__(
            f"Agent communication failed ({agent_id}): {detail}",
            code="AGENT_COMMUNICATION_ERROR",
        )


# --- Workflow errors ---


class SagaCompensationError(HealthcareError):
    def __init__(self, workflow_id: str, step: str, detail: str) -> None:
        super().__init__(
            f"Saga compensation failed for {workflow_id} at step {step}: {detail}",
            code="SAGA_COMPENSATION_ERROR",
        )


class IdempotencyConflictError(HealthcareError):
    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            f"Operation already completed with idempotency key: {idempotency_key}",
            code="IDEMPOTENCY_CONFLICT",
        )


# --- Terminology errors ---


class InvalidTerminologyCodeError(HealthcareError):
    def __init__(self, system: str, code: str, suggestion: str | None = None) -> None:
        msg = f"Invalid {system} code: {code}"
        if suggestion:
            msg += f" (did you mean: {suggestion}?)"
        super().__init__(msg, code="INVALID_TERMINOLOGY_CODE")
        self.system = system
        self.terminology_code = code
        self.suggestion = suggestion
