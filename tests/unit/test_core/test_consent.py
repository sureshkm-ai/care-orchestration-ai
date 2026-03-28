"""Tests for consent management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.core.consent.manager import (
    get_patient_consents,
    record_break_glass,
    revoke_consent,
    store_consent,
    verify_consent,
)
from src.core.consent.models import ConsentRecord, ConsentScope, ConsentStatus
from src.core.errors import ConsentDeniedError, ConsentRequiredError


def _make_consent(patient_id: str = "P001") -> ConsentRecord:
    return ConsentRecord(
        consent_id="C001",
        patient_id=patient_id,
        status=ConsentStatus.ACTIVE,
        scopes=[
            ConsentScope(
                data_types=["demographics", "labs", "conditions"],
                permitted_uses=["treatment", "care_coordination"],
                permitted_agents=["triage_agent", "care_coordinator"],
            )
        ],
    )


class TestConsentVerification:
    def test_verify_consent_passes(self) -> None:
        consent = _make_consent()
        store_consent(consent)
        result = verify_consent("P001", "demographics", "treatment", "triage_agent")
        assert result.consent_id == "C001"

    def test_verify_consent_no_consent_raises(self) -> None:
        with pytest.raises(ConsentRequiredError):
            verify_consent("P999", "demographics", "treatment", "triage_agent")

    def test_verify_consent_wrong_agent_raises(self) -> None:
        store_consent(_make_consent())
        with pytest.raises(ConsentDeniedError):
            verify_consent("P001", "demographics", "treatment", "pharmacy_agent")

    def test_verify_consent_wrong_use_raises(self) -> None:
        store_consent(_make_consent())
        with pytest.raises(ConsentDeniedError):
            verify_consent("P001", "demographics", "research", "triage_agent")

    def test_revoke_consent(self) -> None:
        store_consent(_make_consent())
        revoke_consent("P001", "C001", "patient request")
        consents = get_patient_consents("P001")
        assert consents[0].status == ConsentStatus.REVOKED
        with pytest.raises(ConsentDeniedError):
            verify_consent("P001", "demographics", "treatment", "triage_agent")

    def test_wildcard_agent(self) -> None:
        consent = ConsentRecord(
            consent_id="C002",
            patient_id="P002",
            scopes=[
                ConsentScope(
                    data_types=["demographics"],
                    permitted_uses=["treatment"],
                    permitted_agents=["*"],
                )
            ],
        )
        store_consent(consent)
        result = verify_consent("P002", "demographics", "treatment", "any_agent")
        assert result.consent_id == "C002"

    def test_expired_scope(self) -> None:
        consent = ConsentRecord(
            consent_id="C003",
            patient_id="P003",
            scopes=[
                ConsentScope(
                    data_types=["demographics"],
                    permitted_uses=["treatment"],
                    permitted_agents=["*"],
                    valid_until=datetime.now(UTC) - timedelta(days=1),
                )
            ],
        )
        store_consent(consent)
        with pytest.raises(ConsentDeniedError):
            verify_consent("P003", "demographics", "treatment", "triage_agent")


class TestBreakGlass:
    def test_record_break_glass(self) -> None:
        record = record_break_glass("P001", "triage_agent", "cardiac arrest")
        assert record.patient_id == "P001"
        assert record.accessor == "triage_agent"
        assert record.reviewed is False
