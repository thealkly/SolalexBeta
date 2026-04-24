"""Shared fakes and factories for Story 3.1 controller/executor unit tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from solalex.adapters.base import DeviceRecord
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import upsert_device


class FakeHaClient:
    """Minimal stand-in for HaWebSocketClient for dispatcher/controller tests."""

    def __init__(
        self,
        *,
        raise_on_call: BaseException | None = None,
    ) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self._raise = raise_on_call

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append((domain, service, dict(service_data or {})))
        if self._raise is not None:
            raise self._raise
        return {"id": 1, "type": "result", "success": True, "result": {}}


def make_db_factory(
    db_path: Path,
) -> Callable[[], Any]:
    """Return a zero-arg factory yielding aiosqlite connections on db_path."""

    def _factory() -> Any:
        return connection_context(db_path)

    return _factory


@asynccontextmanager
async def open_conn(db_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    async with connection_context(db_path) as conn:
        yield conn


async def seeded_device(
    db_path: Path,
    *,
    adapter_key: str = "hoymiles",
    entity_id: str = "number.opendtu_limit_nonpersistent_absolute",
    role: str = "wr_limit",
    commissioned: bool = True,
) -> DeviceRecord:
    """Apply migrations + insert a single device, return the stored record."""
    await run_migration(db_path)
    async with connection_context(db_path) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type=adapter_key,
                role=role,
                entity_id=entity_id,
                adapter_key=adapter_key,
            ),
        )
        if commissioned:
            ts = datetime.now(tz=UTC).isoformat()
            await conn.execute(
                "UPDATE devices SET commissioned_at = ? WHERE entity_id = ?",
                (ts, entity_id),
            )
            await conn.commit()
        async with conn.execute(
            "SELECT id, commissioned_at FROM devices WHERE entity_id = ?",
            (entity_id,),
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    device_id = int(row[0])
    commissioned_at: datetime | None = None
    if row[1] is not None:
        commissioned_at = datetime.fromisoformat(str(row[1]))
    return DeviceRecord(
        id=device_id,
        type=adapter_key,
        role=role,
        entity_id=entity_id,
        adapter_key=adapter_key,
        commissioned_at=commissioned_at,
    )
