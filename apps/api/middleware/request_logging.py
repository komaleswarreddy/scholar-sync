"""
Request logging middleware.

Uses a low-level ASGI wrapper so logs are emitted reliably for normal, error,
and streaming responses under uvicorn --reload.
"""

from __future__ import annotations

import time
import traceback
from typing import Optional

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestLoggingMiddleware:
    """Emit request start/end/error logs to stdout for every HTTP request."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method") or "UNKNOWN")
        path = str(scope.get("path") or "")
        query_bytes = scope.get("query_string", b"") or b""
        query = query_bytes.decode("utf-8", errors="ignore")
        full_path = f"{path}?{query}" if query else path
        client = scope.get("client")
        client_host = client[0] if client else "unknown"
        start = time.perf_counter()
        status_code: Optional[int] = None

        print(f"[REQ] {method} {full_path} client={client_host}")

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status") or 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            state = scope.get("state")
            tenant_id = getattr(state, "tenant_id", None) if state is not None else None
            user_id = getattr(state, "user_id", None) if state is not None else None
            print(
                f"[REQ_ERR] {method} {full_path} "
                f"tenant={tenant_id} user={user_id} "
                f"duration_ms={duration_ms:.1f} "
                f"error={type(exc).__name__}: {exc}"
            )
            print(traceback.format_exc())
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        state = scope.get("state")
        tenant_id = getattr(state, "tenant_id", None) if state is not None else None
        user_id = getattr(state, "user_id", None) if state is not None else None
        print(
            f"[REQ_OK] {method} {full_path} "
            f"status={status_code or 0} "
            f"tenant={tenant_id} user={user_id} "
            f"duration_ms={duration_ms:.1f}"
        )
