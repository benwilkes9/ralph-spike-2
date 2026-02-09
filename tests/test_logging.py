"""Tests for structured request/response logging middleware.

Verifies that every HTTP request produces a structured JSON log entry
with method, path, query_string, status_code, and duration_ms.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast

import pytest
from httpx import AsyncClient


@pytest.fixture
def log_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Capture log records from the todo_api logger."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        pass
    return caplog.records


async def _get_log_entry(
    caplog: pytest.LogCaptureFixture,
) -> dict[str, Any]:
    """Extract the single request log entry from captured logs.

    Filters to only todo_api INFO records that contain request data.
    """
    entries: list[dict[str, Any]] = []
    for record in caplog.records:
        if record.name == "todo_api" and record.levelno == logging.INFO:
            msg: Any = record.msg
            if isinstance(msg, dict):
                entries.append(cast("dict[str, Any]", msg))
    assert len(entries) == 1, f"Expected 1 log entry, got {len(entries)}"
    return entries[0]


# --- AC1: Every HTTP request produces exactly one structured log entry ---


@pytest.mark.asyncio
async def test_get_request_produces_log_entry(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GET /todos produces exactly one log entry."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos")
    entry = await _get_log_entry(caplog)
    assert entry["method"] == "GET"
    assert entry["path"] == "/todos"


@pytest.mark.asyncio
async def test_post_request_produces_log_entry(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """POST /todos produces exactly one log entry."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.post("/todos", json={"title": "Log test"})
    entry = await _get_log_entry(caplog)
    assert entry["method"] == "POST"
    assert entry["path"] == "/todos"


@pytest.mark.asyncio
async def test_delete_request_produces_log_entry(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """DELETE /todos/{id} produces exactly one log entry."""
    resp = await client.post("/todos", json={"title": "To delete"})
    todo_id = resp.json()["id"]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.delete(f"/todos/{todo_id}")
    entry = await _get_log_entry(caplog)
    assert entry["method"] == "DELETE"
    assert entry["path"] == f"/todos/{todo_id}"


# --- AC2: Log entry contains all required fields ---


@pytest.mark.asyncio
async def test_log_entry_has_all_required_fields(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log entry contains method, path, query_string, status_code, duration_ms."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos")
    entry = await _get_log_entry(caplog)
    assert "method" in entry
    assert "path" in entry
    assert "query_string" in entry
    assert "status_code" in entry
    assert "duration_ms" in entry


# --- AC3: duration_ms is a non-negative float ---


@pytest.mark.asyncio
async def test_duration_ms_is_non_negative_float(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """duration_ms is a non-negative number."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos")
    entry = await _get_log_entry(caplog)
    assert isinstance(entry["duration_ms"], int | float)
    assert entry["duration_ms"] >= 0


# --- AC4: status_code matches actual HTTP response ---


@pytest.mark.asyncio
async def test_status_code_200_on_success(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """200 status logged for successful GET /todos."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.get("/todos")
    assert resp.status_code == 200
    entry = await _get_log_entry(caplog)
    assert entry["status_code"] == 200


@pytest.mark.asyncio
async def test_status_code_201_on_create(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """201 status logged for successful POST /todos."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.post("/todos", json={"title": "Created item"})
    assert resp.status_code == 201
    entry = await _get_log_entry(caplog)
    assert entry["status_code"] == 201


@pytest.mark.asyncio
async def test_status_code_204_on_delete(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """204 status logged for successful DELETE."""
    resp = await client.post("/todos", json={"title": "Delete me"})
    todo_id = resp.json()["id"]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.delete(f"/todos/{todo_id}")
    assert resp.status_code == 204
    entry = await _get_log_entry(caplog)
    assert entry["status_code"] == 204


@pytest.mark.asyncio
async def test_status_code_404_on_not_found(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """404 status logged for GET /todos/999."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.get("/todos/999")
    assert resp.status_code == 404
    entry = await _get_log_entry(caplog)
    assert entry["status_code"] == 404


@pytest.mark.asyncio
async def test_status_code_422_on_validation_error(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """422 status logged for invalid path param."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.get("/todos/abc")
    assert resp.status_code == 422
    entry = await _get_log_entry(caplog)
    assert entry["status_code"] == 422


@pytest.mark.asyncio
async def test_status_code_409_on_conflict(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """409 status logged for duplicate title."""
    await client.post("/todos", json={"title": "Unique title"})
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.post("/todos", json={"title": "Unique title"})
    assert resp.status_code == 409
    entry = await _get_log_entry(caplog)
    assert entry["status_code"] == 409


# --- AC5: method and path match the request ---


@pytest.mark.asyncio
async def test_method_and_path_for_put(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """PUT method and path logged correctly."""
    resp = await client.post("/todos", json={"title": "PUT test"})
    todo_id = resp.json()["id"]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.put(f"/todos/{todo_id}", json={"title": "Updated"})
    entry = await _get_log_entry(caplog)
    assert entry["method"] == "PUT"
    assert entry["path"] == f"/todos/{todo_id}"


@pytest.mark.asyncio
async def test_method_and_path_for_patch(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """PATCH method and path logged correctly."""
    resp = await client.post("/todos", json={"title": "PATCH test"})
    todo_id = resp.json()["id"]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.patch(f"/todos/{todo_id}", json={"completed": True})
    entry = await _get_log_entry(caplog)
    assert entry["method"] == "PATCH"
    assert entry["path"] == f"/todos/{todo_id}"


@pytest.mark.asyncio
async def test_method_and_path_for_complete(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """POST /todos/{id}/complete logs correct method and path."""
    resp = await client.post("/todos", json={"title": "Complete test"})
    todo_id = resp.json()["id"]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.post(f"/todos/{todo_id}/complete")
    entry = await _get_log_entry(caplog)
    assert entry["method"] == "POST"
    assert entry["path"] == f"/todos/{todo_id}/complete"


@pytest.mark.asyncio
async def test_method_and_path_for_incomplete(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """POST /todos/{id}/incomplete logs correct method and path."""
    resp = await client.post("/todos", json={"title": "Incomplete test"})
    todo_id = resp.json()["id"]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.post(f"/todos/{todo_id}/incomplete")
    entry = await _get_log_entry(caplog)
    assert entry["method"] == "POST"
    assert entry["path"] == f"/todos/{todo_id}/incomplete"


# --- AC6: query_string handling ---


@pytest.mark.asyncio
async def test_query_string_empty_when_no_params(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """query_string is empty string when no query parameters."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos")
    entry = await _get_log_entry(caplog)
    assert entry["query_string"] == ""


@pytest.mark.asyncio
async def test_query_string_with_params(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """query_string contains raw query string when params present."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos?completed=true&sort=title")
    entry = await _get_log_entry(caplog)
    assert "completed=true" in entry["query_string"]
    assert "sort=title" in entry["query_string"]


@pytest.mark.asyncio
async def test_query_string_with_search(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """query_string captures search parameter."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos?search=milk")
    entry = await _get_log_entry(caplog)
    assert "search=milk" in entry["query_string"]


# --- AC7: Logger name is todo_api ---


@pytest.mark.asyncio
async def test_logger_name_is_todo_api(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log records come from the todo_api logger."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos")
    todo_records = [r for r in caplog.records if r.name == "todo_api"]
    assert len(todo_records) >= 1


# --- AC8: Log format is valid JSON ---


@pytest.mark.asyncio
async def test_log_format_is_valid_json(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log output can be parsed as valid JSON."""
    todo_logger = logging.getLogger("todo_api")
    # Ensure handler with JSON formatter is present
    from ralf_spike_2.logging_middleware import setup_logging

    setup_logging()
    with caplog.at_level(logging.INFO, logger="todo_api"):
        await client.get("/todos")
    # Get the formatted output from the handler
    for record in caplog.records:
        if record.name == "todo_api":
            for handler in todo_logger.handlers:
                formatted = handler.format(record)
                parsed = json.loads(formatted)
                assert "method" in parsed
                assert "path" in parsed
                break


# --- AC9: Logging does not alter request/response behavior ---


@pytest.mark.asyncio
async def test_logging_does_not_alter_get_response(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """GET /todos still returns 200 with correct body."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.get("/todos")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_logging_does_not_alter_create_response(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """POST /todos still returns 201 with correct body shape."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.post("/todos", json={"title": "Logging ok"})
    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) == {"id", "title", "completed"}
    assert body["title"] == "Logging ok"
    assert body["completed"] is False


@pytest.mark.asyncio
async def test_logging_does_not_alter_error_response(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Error responses still have correct format with logging enabled."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.get("/todos/abc")
    assert resp.status_code == 422
    assert resp.json() == {"detail": "id must be a positive integer"}


# --- _JsonFormatter non-dict message branch ---


def test_json_formatter_non_dict_message() -> None:
    """JSON formatter formats non-dict messages as {"message": "..."}."""
    from ralf_spike_2.logging_middleware import setup_logging

    setup_logging()
    todo_logger = logging.getLogger("todo_api")
    # Get the JSON formatter from the handler
    formatter = todo_logger.handlers[0].formatter
    assert formatter is not None
    record = logging.LogRecord(
        name="todo_api",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="plain string",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed == {"message": "plain string"}


# --- setup_logging() idempotency ---


def test_setup_logging_idempotent() -> None:
    """Calling setup_logging() multiple times adds only one handler."""
    from ralf_spike_2.logging_middleware import setup_logging

    todo_logger = logging.getLogger("todo_api")
    initial_count = len(todo_logger.handlers)
    setup_logging()
    setup_logging()
    setup_logging()
    # Should not have added more than one handler total
    assert len(todo_logger.handlers) <= initial_count + 1


# --- Log query_string on 422 error response ---


@pytest.mark.asyncio
async def test_log_query_string_on_422(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log entry captures query_string even when request returns 422."""
    with caplog.at_level(logging.INFO, logger="todo_api"):
        resp = await client.get("/todos?completed=yes")
    assert resp.status_code == 422
    entry = await _get_log_entry(caplog)
    assert entry["status_code"] == 422
    assert "completed=yes" in entry["query_string"]
