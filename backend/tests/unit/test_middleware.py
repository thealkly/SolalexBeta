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
    resp = client.post("/api/v1/devices/", json={"hardware_type": "hoymiles"})
    assert resp.status_code == 422
    data = resp.json()
    # The detail should contain German text / field info
    assert len(data["detail"]) > 0
