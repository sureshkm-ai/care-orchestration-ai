"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Provide a temporary database path for tests."""
    return tmp_path / "test.db"


@pytest.fixture(autouse=True)
def _reset_consent_store() -> None:
    """Reset the in-memory consent store between tests."""
    from src.core.consent.manager import clear_consent_store

    clear_consent_store()


@pytest.fixture(autouse=True)
def _reset_terminology() -> None:
    """Reset terminology registries between tests."""
    from src.core.terminology.service import clear_registries

    clear_registries()
