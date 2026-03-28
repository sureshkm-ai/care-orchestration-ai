"""HIPAA-compliant audit logger with hash-chained entries.

Each audit event includes the SHA-256 hash of the previous event,
creating a tamper-resistant chain. Events are written as structured JSON
and stored in SQLite (local) or DynamoDB + CloudTrail (AWS).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from src.core.audit.models import AuditAction, AuditEvent, AuditOutcome
from src.core.observability.correlation import get_correlation_id
from src.core.observability.logging import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Append-only, hash-chained audit logger for HIPAA compliance."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._previous_hash = ""
        self._initialized = False

    async def initialize(self) -> None:
        """Create the audit table if it doesn't exist."""
        if self._initialized:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    patient_id TEXT,
                    outcome TEXT NOT NULL,
                    correlation_id TEXT,
                    consent_reference TEXT,
                    data_classification TEXT,
                    details TEXT,
                    previous_hash TEXT,
                    event_hash TEXT NOT NULL
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_patient ON audit_events(patient_id)"
            )
            await db.commit()

            # Load the last hash for chain continuity
            cursor = await db.execute(
                "SELECT event_hash FROM audit_events ORDER BY rowid DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                self._previous_hash = row[0]

        self._initialized = True

    def _compute_hash(self, event: AuditEvent) -> str:
        """Compute SHA-256 hash of the event for tamper resistance."""
        data = event.model_dump_json(exclude={"event_hash"})
        return hashlib.sha256(data.encode()).hexdigest()

    async def log_event(
        self,
        *,
        actor: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        outcome: AuditOutcome,
        patient_id: str | None = None,
        consent_reference: str | None = None,
        data_classification: str = "operational",
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log an audit event with hash chaining."""
        await self.initialize()

        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            outcome=outcome,
            correlation_id=get_correlation_id(),
            consent_reference=consent_reference,
            data_classification=data_classification,
            details={k: str(v) for k, v in details.items()} if details else None,
            previous_hash=self._previous_hash,
        )
        event.event_hash = self._compute_hash(event)
        self._previous_hash = event.event_hash

        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                """INSERT INTO audit_events
                   (event_id, timestamp, actor, action, resource_type, resource_id,
                    patient_id, outcome, correlation_id, consent_reference,
                    data_classification, details, previous_hash, event_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.actor,
                    event.action.value,
                    event.resource_type,
                    event.resource_id,
                    event.patient_id,
                    event.outcome.value,
                    event.correlation_id,
                    event.consent_reference,
                    event.data_classification,
                    json.dumps(event.details) if event.details else None,
                    event.previous_hash,
                    event.event_hash,
                ),
            )
            await db.commit()

        await logger.ainfo(
            "audit_event",
            event_id=event.event_id,
            actor=event.actor,
            action=event.action.value,
            resource_type=event.resource_type,
            outcome=event.outcome.value,
        )
        return event

    async def log_phi_access(
        self,
        *,
        actor: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        patient_id: str,
        outcome: AuditOutcome,
        consent_reference: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Convenience method for logging PHI access events."""
        return await self.log_event(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            outcome=outcome,
            consent_reference=consent_reference,
            data_classification="phi",
            details=details,
        )

    async def query_by_correlation_id(self, correlation_id: str) -> list[AuditEvent]:
        """Query audit events by correlation ID."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM audit_events WHERE correlation_id = ? ORDER BY timestamp",
                (correlation_id,),
            )
            rows = await cursor.fetchall()
            return [
                AuditEvent(
                    event_id=row["event_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    actor=row["actor"],
                    action=AuditAction(row["action"]),
                    resource_type=row["resource_type"],
                    resource_id=row["resource_id"],
                    patient_id=row["patient_id"],
                    outcome=AuditOutcome(row["outcome"]),
                    correlation_id=row["correlation_id"],
                    consent_reference=row["consent_reference"],
                    data_classification=row["data_classification"],
                    details=json.loads(row["details"]) if row["details"] else None,
                    previous_hash=row["previous_hash"],
                    event_hash=row["event_hash"],
                )
                for row in rows
            ]
