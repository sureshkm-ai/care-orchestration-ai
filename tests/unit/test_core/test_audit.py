"""Tests for HIPAA audit logger."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.audit.logger import AuditLogger
from src.core.audit.models import AuditAction, AuditOutcome
from src.core.observability.correlation import set_correlation_id


@pytest.fixture
def audit_logger(tmp_db_path: Path) -> AuditLogger:
    return AuditLogger(tmp_db_path)


class TestAuditLogger:
    async def test_log_event(self, audit_logger: AuditLogger) -> None:
        event = await audit_logger.log_event(
            actor="triage_agent",
            action=AuditAction.READ,
            resource_type="Patient",
            resource_id="P001",
            outcome=AuditOutcome.SUCCESS,
        )
        assert event.event_id
        assert event.actor == "triage_agent"
        assert event.event_hash

    async def test_hash_chain(self, audit_logger: AuditLogger) -> None:
        e1 = await audit_logger.log_event(
            actor="agent1",
            action=AuditAction.READ,
            resource_type="Patient",
            resource_id="P001",
            outcome=AuditOutcome.SUCCESS,
        )
        e2 = await audit_logger.log_event(
            actor="agent2",
            action=AuditAction.READ,
            resource_type="Patient",
            resource_id="P002",
            outcome=AuditOutcome.SUCCESS,
        )
        assert e2.previous_hash == e1.event_hash

    async def test_log_phi_access(self, audit_logger: AuditLogger) -> None:
        event = await audit_logger.log_phi_access(
            actor="triage_agent",
            action=AuditAction.READ,
            resource_type="Patient",
            resource_id="P001",
            patient_id="P001",
            outcome=AuditOutcome.SUCCESS,
            consent_reference="Consent/C001",
        )
        assert event.data_classification == "phi"
        assert event.consent_reference == "Consent/C001"

    async def test_query_by_correlation_id(self, audit_logger: AuditLogger) -> None:
        set_correlation_id("test-corr-123")
        await audit_logger.log_event(
            actor="agent1",
            action=AuditAction.READ,
            resource_type="Patient",
            resource_id="P001",
            outcome=AuditOutcome.SUCCESS,
        )
        await audit_logger.log_event(
            actor="agent2",
            action=AuditAction.CREATE,
            resource_type="Appointment",
            resource_id="A001",
            outcome=AuditOutcome.SUCCESS,
        )
        events = await audit_logger.query_by_correlation_id("test-corr-123")
        assert len(events) == 2
        assert events[0].actor == "agent1"
        assert events[1].actor == "agent2"
