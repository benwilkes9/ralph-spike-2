"""ASGI middleware for structured request/response logging."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, cast

logger = logging.getLogger("todo_api")


class _JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        msg: Any = record.msg
        if isinstance(msg, dict):
            data: dict[str, Any] = cast("dict[str, Any]", msg)
        else:
            data = {"message": record.getMessage()}
        return json.dumps(data, default=str)


def setup_logging() -> None:
    """Configure the todo_api logger with JSON formatting to stdout."""
    todo_logger = logging.getLogger("todo_api")
    if not todo_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        todo_logger.addHandler(handler)
        todo_logger.setLevel(logging.INFO)


class LoggingMiddleware:
    """ASGI middleware that logs each request/response as structured JSON."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        path: str = scope.get("path", "")
        query_string_bytes: bytes = scope.get("query_string", b"")
        query_string = query_string_bytes.decode("utf-8", errors="replace")

        status_code = 0
        start_time = time.monotonic()

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            {
                "method": method,
                "path": path,
                "query_string": query_string,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 3),
            }
        )
