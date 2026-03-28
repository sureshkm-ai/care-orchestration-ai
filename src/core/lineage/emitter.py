"""Lineage event emitter -- stores events in SQLite (local) or DynamoDB+S3 (AWS).

Provides an async interface for recording lineage events.
"""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from src.core.lineage.events import HealthcareLineageEvent
from src.core.observability.logging import get_logger

logger = get_logger(__name__)


class LineageEmitter:
    """Emits lineage events to persistent storage."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS lineage_events (
                    run_id TEXT NOT NULL,
                    parent_run_id TEXT,
                    job_namespace TEXT NOT NULL,
                    job_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    correlation_id TEXT,
                    agent_id TEXT,
                    patient_id TEXT,
                    consent_reference TEXT,
                    data_classification TEXT,
                    mcp_tool_name TEXT,
                    a2a_task_id TEXT,
                    workflow_id TEXT,
                    duration_ms REAL,
                    error_message TEXT,
                    inputs TEXT,
                    outputs TEXT,
                    PRIMARY KEY (run_id, event_type)
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_correlation "
                "ON lineage_events(correlation_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_patient ON lineage_events(patient_id)"
            )
            await db.commit()
        self._initialized = True

    async def emit(self, event: HealthcareLineageEvent) -> None:
        """Emit a lineage event to the store."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                """INSERT OR REPLACE INTO lineage_events
                   (run_id, parent_run_id, job_namespace, job_name, event_type,
                    event_time, correlation_id, agent_id, patient_id,
                    consent_reference, data_classification, mcp_tool_name,
                    a2a_task_id, workflow_id, duration_ms, error_message,
                    inputs, outputs)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.run_id,
                    event.parent_run_id,
                    event.job_namespace,
                    event.job_name,
                    event.event_type.value,
                    event.event_time.isoformat(),
                    event.correlation_id,
                    event.agent_id,
                    event.patient_id,
                    event.consent_reference,
                    event.data_classification,
                    event.mcp_tool_name,
                    event.a2a_task_id,
                    event.workflow_id,
                    event.duration_ms,
                    event.error_message,
                    json.dumps([d.model_dump() for d in event.inputs]),
                    json.dumps([d.model_dump() for d in event.outputs]),
                ),
            )
            await db.commit()

    async def query_by_correlation_id(self, correlation_id: str) -> list[HealthcareLineageEvent]:
        """Query lineage events by correlation ID."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM lineage_events WHERE correlation_id = ? ORDER BY event_time",
                (correlation_id,),
            )
            rows = await cursor.fetchall()
            return [self._row_to_event(row) for row in rows]

    @staticmethod
    def _row_to_event(row: aiosqlite.Row) -> HealthcareLineageEvent:
        from datetime import datetime

        from src.core.lineage.events import DatasetRef, RunState

        inputs_raw = json.loads(row["inputs"]) if row["inputs"] else []
        outputs_raw = json.loads(row["outputs"]) if row["outputs"] else []
        return HealthcareLineageEvent(
            run_id=row["run_id"],
            parent_run_id=row["parent_run_id"],
            job_namespace=row["job_namespace"],
            job_name=row["job_name"],
            event_type=RunState(row["event_type"]),
            event_time=datetime.fromisoformat(row["event_time"]),
            correlation_id=row["correlation_id"] or "",
            agent_id=row["agent_id"] or "",
            patient_id=row["patient_id"],
            consent_reference=row["consent_reference"],
            data_classification=row["data_classification"] or "operational",
            mcp_tool_name=row["mcp_tool_name"],
            a2a_task_id=row["a2a_task_id"],
            workflow_id=row["workflow_id"],
            duration_ms=row["duration_ms"],
            error_message=row["error_message"],
            inputs=[DatasetRef(**d) for d in inputs_raw],
            outputs=[DatasetRef(**d) for d in outputs_raw],
        )
