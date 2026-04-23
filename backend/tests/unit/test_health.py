"""Smoke-test the health endpoint.

Story 1.3 extends the payload from the Story 1.1 ``{"status": "ok"}``
to ``{"status": "ok", "ha_ws_connected": bool, "uptime_seconds": int}``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_status_shape(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # Supervisor token is absent in tests — the reconnect task is skipped
    # so the session flag stays False. This directly exercises AC 6 (the
    # payload, not the HTTP code, carries upstream health).
    assert body["ha_ws_connected"] is False
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0
    # AC 4 + CLAUDE.md rule 4 — no wrapper, direct object.
    assert "data" not in body
    assert "success" not in body


def test_root_returns_json_when_frontend_absent(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
