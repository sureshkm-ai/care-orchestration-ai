"""Human review queue backed by SQLite (local) or DynamoDB (AWS).

Provides CRUD operations for ReviewTask and monitoring for SLA compliance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from src.core.human_review.models import ReviewDecision, ReviewStatus, ReviewTask
from src.core.observability.logging import get_logger

logger = get_logger(__name__)


class ReviewQueue:
    """Clinician review worklist with SLA monitoring."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS review_tasks (
                    task_id TEXT PRIMARY KEY,
                    task_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    patient_id TEXT,
                    workflow_id TEXT,
                    created_at TEXT NOT NULL,
                    sla_deadline TEXT NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_review_status ON review_tasks(status)")
            await db.commit()
        self._initialized = True

    async def enqueue(self, task: ReviewTask) -> ReviewTask:
        """Add a review task to the queue."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                """INSERT INTO review_tasks
                   (task_id, task_json, status, patient_id, workflow_id, created_at, sla_deadline)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.task_id,
                    task.model_dump_json(),
                    task.status.value,
                    task.patient_id,
                    task.workflow_id,
                    task.created_at.isoformat(),
                    task.sla_deadline.isoformat(),
                ),
            )
            await db.commit()
        await logger.ainfo(
            "review_task_enqueued",
            task_id=task.task_id,
            trigger=task.escalation_trigger,
            patient_id=task.patient_id,
        )
        return task

    async def get(self, task_id: str) -> ReviewTask | None:
        """Get a review task by ID."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            cursor = await db.execute(
                "SELECT task_json FROM review_tasks WHERE task_id = ?", (task_id,)
            )
            row = await cursor.fetchone()
            if row:
                return ReviewTask.model_validate_json(row[0])
            return None

    async def resolve(
        self,
        task_id: str,
        decision: ReviewDecision,
        override_reason: str | None = None,
    ) -> ReviewTask | None:
        """Resolve a review task with a clinician's decision."""
        task = await self.get(task_id)
        if task is None:
            return None

        task.decision = decision
        task.status = decision.status
        task.resolved_at = datetime.now(UTC)
        task.override_reason = override_reason

        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                "UPDATE review_tasks SET task_json = ?, status = ? WHERE task_id = ?",
                (task.model_dump_json(), task.status.value, task_id),
            )
            await db.commit()

        await logger.ainfo(
            "review_task_resolved",
            task_id=task_id,
            status=decision.status.value,
            reviewer=decision.reviewer_id,
        )
        return task

    async def get_pending(self) -> list[ReviewTask]:
        """Get all pending review tasks."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            cursor = await db.execute(
                "SELECT task_json FROM review_tasks WHERE status = ?",
                (ReviewStatus.PENDING.value,),
            )
            rows = await cursor.fetchall()
            return [ReviewTask.model_validate_json(row[0]) for row in rows]

    async def get_overdue(self) -> list[ReviewTask]:
        """Get review tasks that have exceeded their SLA deadline."""
        await self.initialize()
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(str(self._db_path)) as db:
            cursor = await db.execute(
                "SELECT task_json FROM review_tasks WHERE status = ? AND sla_deadline < ?",
                (ReviewStatus.PENDING.value, now),
            )
            rows = await cursor.fetchall()
            return [ReviewTask.model_validate_json(row[0]) for row in rows]
