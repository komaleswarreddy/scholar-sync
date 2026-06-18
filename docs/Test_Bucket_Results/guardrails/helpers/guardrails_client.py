"""Guardrails chat wrapper for GRD integration tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from tests.helpers.chat_client import ChatStreamResult, stream_chat


@dataclass
class GuardrailChatResult:
    """Normalized chat outcome for guardrails assertions."""

    text: str = ""
    error: Optional[str] = None
    http_status: Optional[int] = None
    events: List[str] = field(default_factory=list)
    done_payload: Optional[Dict[str, Any]] = None
    raw: Optional[ChatStreamResult] = None

    @property
    def blocked(self) -> bool:
        if self.http_status == 429:
            return True
        if self.error:
            return True
        lower = (self.text or "").lower()
        if not lower.strip() and self.done_payload and self.done_payload.get("moderated"):
            return True
        return False


def stream_guardrail_check(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    message: str,
    active_source_ids: Optional[List[str]] = None,
    **kwargs: Any,
) -> GuardrailChatResult:
    """Stream chat and normalize for guardrails test assertions."""
    result = stream_chat(
        client,
        base_url=base_url,
        token=token,
        message=message,
        active_source_ids=active_source_ids,
        **kwargs,
    )
    out = GuardrailChatResult(
        text=result.text or "",
        error=result.error,
        events=list(result.events),
        done_payload=result.done_payload,
        raw=result,
    )
    if result.error and result.error.startswith("HTTP "):
        try:
            code = int(result.error.split()[1].rstrip(":"))
            out.http_status = code
        except (IndexError, ValueError):
            pass
    return out


def post_chat_raw(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    message: str,
    active_source_ids: Optional[List[str]] = None,
    include_ncert_global: bool = False,
) -> httpx.Response:
    """Non-streaming POST for rate-limit (429) checks — closes body early when not 429."""
    payload: Dict[str, Any] = {
        "message": message,
        "history": [],
        "active_source_ids": list(active_source_ids or []),
    }
    if include_ncert_global:
        payload["include_ncert_global"] = True
    with client.stream(
        "POST",
        f"{base_url}/api/v1/chat/stream",
        headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
        json=payload,
        timeout=60.0,
    ) as response:
        status = response.status_code
        content = response.read() if status == 429 else b""
        return httpx.Response(
            status_code=status,
            headers=dict(response.headers),
            content=content,
            request=response.request,
        )
