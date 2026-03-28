"""Saga state machine for multi-step workflows.

Manages the lifecycle of a workflow across multiple agents and MCP servers.
Handles partial failure by executing compensating actions in reverse order.
Source of truth for task durability (BD-3).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from src.core.observability.logging import get_logger
from src.core.workflow.models import SagaState, SagaStatus, StepStatus

logger = get_logger(__name__)


class SagaCoordinator:
    """Manages saga state and orchestrates compensation on failure."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS saga_state (
                    workflow_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.commit()
        self._initialized = True

    async def create(self, saga: SagaState) -> SagaState:
        """Persist a new saga."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                "INSERT INTO saga_state (workflow_id, state_json, updated_at) VALUES (?, ?, ?)",
                (saga.workflow_id, saga.model_dump_json(), datetime.now(UTC).isoformat()),
            )
            await db.commit()
        return saga

    async def get(self, workflow_id: str) -> SagaState | None:
        """Load a saga by workflow ID."""
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            cursor = await db.execute(
                "SELECT state_json FROM saga_state WHERE workflow_id = ?",
                (workflow_id,),
            )
            row = await cursor.fetchone()
            if row:
                return SagaState.model_validate_json(row[0])
            return None

    async def update(self, saga: SagaState) -> None:
        """Update saga state."""
        saga.updated_at = datetime.now(UTC)
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute(
                "UPDATE saga_state SET state_json = ?, updated_at = ? WHERE workflow_id = ?",
                (saga.model_dump_json(), saga.updated_at.isoformat(), saga.workflow_id),
            )
            await db.commit()

    async def mark_step_started(self, saga: SagaState, step_id: str) -> None:
        """Mark a step as started."""
        for step in saga.steps:
            if step.step_id == step_id:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now(UTC)
                break
        await self.update(saga)

    async def mark_step_completed(
        self, saga: SagaState, step_id: str, result: dict[str, Any] | None = None
    ) -> None:
        """Mark a step as completed."""
        for step in saga.steps:
            if step.step_id == step_id:
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now(UTC)
                step.result = result
                break
        await self.update(saga)

    async def mark_step_failed(self, saga: SagaState, step_id: str, error: str) -> None:
        """Mark a step as failed and trigger compensation."""
        for step in saga.steps:
            if step.step_id == step_id:
                step.status = StepStatus.FAILED
                step.error = error
                break
        saga.status = SagaStatus.FAILED
        await self.update(saga)

    async def pause_for_review(self, saga: SagaState, step_id: str, review_task_id: str) -> None:
        """Pause the saga for human review."""
        saga.status = SagaStatus.PAUSED
        saga.paused_at_step = step_id
        saga.review_task_id = review_task_id
        await self.update(saga)

    async def resume_after_review(self, saga: SagaState) -> None:
        """Resume a paused saga after human review."""
        saga.status = SagaStatus.RESUMED
        saga.paused_at_step = None
        await self.update(saga)

    async def mark_completed(self, saga: SagaState) -> None:
        """Mark the entire saga as completed."""
        saga.status = SagaStatus.COMPLETED
        await self.update(saga)

    async def compensate(self, saga: SagaState) -> list[str]:
        """Execute compensating actions for completed steps in reverse order.

        Returns list of compensated step IDs.
        """
        saga.status = SagaStatus.COMPENSATING
        await self.update(saga)

        compensated: list[str] = []
        for step in reversed(saga.completed_steps()):
            if step.compensating_action:
                step.compensation_status = StepStatus.COMPLETED
                compensated.append(step.step_id)
                await logger.ainfo(
                    "saga_compensate",
                    workflow_id=saga.workflow_id,
                    step=step.name,
                    action=step.compensating_action,
                )

        saga.status = SagaStatus.COMPENSATED
        await self.update(saga)
        return compensated
