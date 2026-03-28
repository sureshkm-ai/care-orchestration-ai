"""Idempotency key management for write operations.

Every write operation accepts an idempotency key. Duplicate submissions
with the same key return the original result instead of creating duplicates.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite


class IdempotencyStore:
    """Stores idempotency keys and their results."""

    def __init__(self, db_path: Path, ttl_hours: int = 24) -> None:
        self._db_path = db_path
        self._ttl_hours = ttl_hours
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(self._db_path)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    key TEXT PRIMARY KEY,
                    result TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()
        self._initialized = True

    async def check_and_set(self, key: str, result: dict[str, Any]) -> dict[str, Any] | None:
        """Check if key exists. If yes, return stored result. If no, store and return None.

        Returns:
            None if key was new (operation should proceed).
            Previous result dict if key already existed (operation is a duplicate).
        """
        await self.initialize()
        async with aiosqlite.connect(str(self._db_path)) as db:
            # Check for existing key
            cursor = await db.execute(
                "SELECT result, created_at FROM idempotency_keys WHERE key = ?",
                (key,),
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0]) if row[0] else {}

            # Store new key
            await db.execute(
                "INSERT INTO idempotency_keys (key, result, created_at) VALUES (?, ?, ?)",
                (key, json.dumps(result), datetime.now(UTC).isoformat()),
            )
            await db.commit()
            return None

    async def cleanup_expired(self) -> int:
        """Remove expired idempotency keys. Returns count of removed keys."""
        await self.initialize()
        cutoff = datetime.now(UTC) - timedelta(hours=self._ttl_hours)
        async with aiosqlite.connect(str(self._db_path)) as db:
            cursor = await db.execute(
                "DELETE FROM idempotency_keys WHERE created_at < ?",
                (cutoff.isoformat(),),
            )
            await db.commit()
            return cursor.rowcount
