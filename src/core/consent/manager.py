"""Consent verification and management.

Enforces scoped consent before any PHI access.
Supports consent revocation and break-glass emergency access.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.core.consent.models import BreakGlassRecord, ConsentRecord, ConsentStatus
from src.core.errors import ConsentDeniedError, ConsentRequiredError
from src.core.observability.logging import get_logger

logger = get_logger(__name__)

# In-memory store for local dev; replaced by DynamoDB in AWS mode
_consent_store: dict[str, list[ConsentRecord]] = {}
_break_glass_store: list[BreakGlassRecord] = []


def store_consent(consent: ConsentRecord) -> None:
    """Store a consent record for a patient."""
    if consent.patient_id not in _consent_store:
        _consent_store[consent.patient_id] = []
    _consent_store[consent.patient_id].append(consent)


def get_patient_consents(patient_id: str) -> list[ConsentRecord]:
    """Get all consent records for a patient."""
    return _consent_store.get(patient_id, [])


def revoke_consent(patient_id: str, consent_id: str, reason: str) -> None:
    """Revoke a specific consent record."""
    for consent in _consent_store.get(patient_id, []):
        if consent.consent_id == consent_id:
            consent.status = ConsentStatus.REVOKED
            consent.revocation_date = datetime.now(UTC)
            consent.revocation_reason = reason
            return


def verify_consent(
    patient_id: str,
    data_type: str,
    use: str,
    agent_id: str,
) -> ConsentRecord:
    """Verify that consent exists for the requested access.

    Returns the matching consent record.
    Raises ConsentRequiredError if no consent exists.
    Raises ConsentDeniedError if consent exists but doesn't permit the access.
    """
    consents = get_patient_consents(patient_id)

    if not consents:
        raise ConsentRequiredError(patient_id, data_type, use)

    for consent in consents:
        if consent.permits(data_type, use, agent_id):
            return consent

    raise ConsentDeniedError(
        patient_id,
        f"No active consent permits {data_type} for {use} by {agent_id}",
    )


def record_break_glass(
    patient_id: str,
    accessor: str,
    reason: str,
) -> BreakGlassRecord:
    """Record a break-glass emergency access event.

    Break-glass allows access without consent in emergencies.
    Must be reviewed within 24 hours.
    """
    record = BreakGlassRecord(
        access_id=str(uuid.uuid4()),
        patient_id=patient_id,
        accessor=accessor,
        reason=reason,
    )
    _break_glass_store.append(record)
    return record


def get_pending_break_glass_reviews() -> list[BreakGlassRecord]:
    """Get break-glass records that haven't been reviewed yet."""
    return [r for r in _break_glass_store if not r.reviewed]


def clear_consent_store() -> None:
    """Clear the in-memory consent store (for testing)."""
    _consent_store.clear()
    _break_glass_store.clear()
