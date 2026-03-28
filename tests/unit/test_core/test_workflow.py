"""Tests for workflow/saga framework."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.workflow.models import SagaState, SagaStatus, SagaStep, StepStatus
from src.core.workflow.saga import SagaCoordinator


@pytest.fixture
def saga_coordinator(tmp_db_path: Path) -> SagaCoordinator:
    return SagaCoordinator(tmp_db_path)


def _make_saga() -> SagaState:
    return SagaState(
        workflow_id="WF001",
        workflow_name="triage_and_route",
        correlation_id="CORR-001",
        patient_id="P001",
        steps=[
            SagaStep(
                step_id="S1",
                name="record_intake",
                compensating_action="void_intake",
            ),
            SagaStep(
                step_id="S2",
                name="assess_triage",
                compensating_action="void_triage",
            ),
            SagaStep(
                step_id="S3",
                name="book_appointment",
                compensating_action="cancel_appointment",
            ),
        ],
    )


class TestSagaCoordinator:
    async def test_create_and_get(self, saga_coordinator: SagaCoordinator) -> None:
        saga = _make_saga()
        await saga_coordinator.create(saga)
        loaded = await saga_coordinator.get("WF001")
        assert loaded is not None
        assert loaded.workflow_name == "triage_and_route"
        assert len(loaded.steps) == 3

    async def test_step_lifecycle(self, saga_coordinator: SagaCoordinator) -> None:
        saga = _make_saga()
        await saga_coordinator.create(saga)

        await saga_coordinator.mark_step_started(saga, "S1")
        assert saga.steps[0].status == StepStatus.RUNNING

        await saga_coordinator.mark_step_completed(saga, "S1", {"intake_id": "I001"})
        assert saga.steps[0].status == StepStatus.COMPLETED
        assert saga.steps[0].result == {"intake_id": "I001"}

    async def test_pause_and_resume(self, saga_coordinator: SagaCoordinator) -> None:
        saga = _make_saga()
        await saga_coordinator.create(saga)

        await saga_coordinator.pause_for_review(saga, "S2", "RT001")
        assert saga.status == SagaStatus.PAUSED
        assert saga.review_task_id == "RT001"

        await saga_coordinator.resume_after_review(saga)
        assert saga.status == SagaStatus.RESUMED
        assert saga.paused_at_step is None

    async def test_compensation(self, saga_coordinator: SagaCoordinator) -> None:
        saga = _make_saga()
        await saga_coordinator.create(saga)

        # Complete first two steps
        saga.steps[0].status = StepStatus.COMPLETED
        saga.steps[1].status = StepStatus.COMPLETED
        await saga_coordinator.update(saga)

        # Fail third step, trigger compensation
        await saga_coordinator.mark_step_failed(saga, "S3", "timeout")
        compensated = await saga_coordinator.compensate(saga)

        assert saga.status == SagaStatus.COMPENSATED
        assert len(compensated) == 2  # S1 and S2 compensated
        assert "S2" in compensated
        assert "S1" in compensated


class TestSagaState:
    def test_current_step(self) -> None:
        saga = _make_saga()
        assert saga.current_step() is not None
        assert saga.current_step().step_id == "S1"  # type: ignore[union-attr]

    def test_completed_steps(self) -> None:
        saga = _make_saga()
        saga.steps[0].status = StepStatus.COMPLETED
        assert len(saga.completed_steps()) == 1
