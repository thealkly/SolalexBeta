"""Unit tests for RFC-7807 exception handler middleware."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_validation_error_returns_problem_json(client: TestClient) -> None:
    """POST /api/v1/devices with invalid body → 422 application/problem+json."""
    resp = client.post("/api/v1/devices/", json={})
    assert resp.status_code == 422
    ct = resp.headers.get("content-type", "")
    assert "problem+json" in ct
    data = resp.json()
    assert data["type"].startswith("urn:solalex:")
    assert "status" in data
    assert "detail" in data


def test_not_found_returns_problem_json(client: TestClient) -> None:
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
    ct = resp.headers.get("content-type", "")
    assert "problem+json" in ct


def test_validation_error_has_german_detail(client: TestClient) -> None:
    resp = client.post("/api/v1/devices/", json={"hardware_type": "generic"})
    assert resp.status_code == 422
    data = resp.json()
    # The detail should contain German text / field info
    assert len(data["detail"]) > 0


def test_legacy_hoymiles_hardware_type_rejected(client: TestClient) -> None:
    """Story 2.4 AC 9 — old `hoymiles` literal must be rejected with 422.

    Locks in the Generic-First Adapter-Refit (2026-04-25): an outdated
    frontend or curl-script sending the legacy key should fail loud at the
    schema layer, not silently fall through to a missing-adapter error
    deep in the dispatcher (Story 2.4 Review P10).
    """
    resp = client.post(
        "/api/v1/devices/",
        json={"hardware_type": "hoymiles", "wr_limit_entity_id": "number.foo"},
    )
    assert resp.status_code == 422
