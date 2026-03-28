"""Database engine factory for per-service SQLite databases.

Each MCP server gets its own database file. In AWS mode,
this is replaced by HealthLake and DynamoDB clients.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.config import get_settings

_engines: dict[str, AsyncEngine] = {}


def get_engine(db_name: str) -> AsyncEngine:
    """Get or create an async SQLAlchemy engine for a named database.

    Args:
        db_name: Logical database name (e.g., "fhir", "scheduling").
                 Will create/use file at {DATABASE_DIR}/{db_name}.db
    """
    if db_name in _engines:
        return _engines[db_name]

    settings = get_settings()
    db_path = settings.db_dir / f"{db_name}.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )
    _engines[db_name] = engine
    return engine


def get_test_engine() -> AsyncEngine:
    """Get an in-memory SQLite engine for testing."""
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )


async def dispose_all_engines() -> None:
    """Dispose all cached engines (for cleanup)."""
    for engine in _engines.values():
        await engine.dispose()
    _engines.clear()
