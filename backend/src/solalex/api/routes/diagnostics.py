"""Diagnostics export endpoint."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from solalex.config import get_settings
from solalex.diagnostics.export import stream_diagnostic_zip

router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


@router.get("/export", response_model=None)
async def export_diagnostics() -> StreamingResponse:
    ts = datetime.now(tz=UTC).replace(microsecond=0)
    settings = get_settings()
    try:
        body = await stream_diagnostic_zip(settings, ts)
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(status_code=500, detail="diagnostics_export_failed") from exc

    return StreamingResponse(
        body,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{_build_export_filename(ts)}"',
            "Cache-Control": "no-store",
        },
    )


def _build_export_filename(ts: datetime) -> str:
    safe_ts = ts.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"solalex-diag_{safe_ts}.zip"
