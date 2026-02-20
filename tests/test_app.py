"""Tests for Task 1: Project Dependencies & App Scaffold."""

from __future__ import annotations

from pydantic import BaseModel
from starlette.testclient import TestClient

from ralf_spike_2.app import app


# Add a test-only endpoint that accepts a Pydantic body to exercise handlers
class _TestBody(BaseModel):
    name: str


@app.post("/test-validation")
async def _test_validation_endpoint(body: _TestBody) -> dict[str, str]:
    return {"name": body.name}


client = TestClient(app, raise_server_exceptions=False)


def test_app_importable() -> None:
    """The FastAPI app instance is importable from the package."""
    from ralf_spike_2.app import app as imported_app

    assert imported_app is not None


def test_health_check_returns_200() -> None:
    """GET / returns a 200 response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_test_client_instantiable() -> None:
    """The TestClient can be instantiated against the app without errors."""
    tc = TestClient(app)
    assert tc is not None
    response = tc.get("/")
    assert response.status_code == 200


def test_validation_error_returns_detail_string() -> None:
    """FastAPI's default 422 response for Pydantic validation errors is
    overridden to use {"detail": "..."} (string, not array)."""
    # Send a request with missing required field to trigger validation
    response = client.post(
        "/test-validation",
        json={"wrong_field": "value"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)
    # Ensure it's NOT the default array format
    assert not isinstance(data["detail"], list)


def test_validation_error_missing_field_message() -> None:
    """Missing field returns {"detail": "<field> is required"}."""
    response = client.post(
        "/test-validation",
        json={},
    )
    assert response.status_code == 422
    data = response.json()
    assert data == {"detail": "name is required"}


def test_validation_error_wrong_type_message() -> None:
    """Wrong type returns 422 with {"detail": "..."}."""
    response = client.post(
        "/test-validation",
        json={"name": 123},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)


def test_malformed_json_returns_422() -> None:
    """Malformed JSON request body returns 422 with {"detail": "..."} format."""
    response = client.post(
        "/test-validation",
        content=b"{invalid json}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], str)
    assert data["detail"] == "Invalid JSON in request body"
