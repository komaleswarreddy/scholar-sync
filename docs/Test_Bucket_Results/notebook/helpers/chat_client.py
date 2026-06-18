"""Chat/stream helpers for retrieval tests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class ChatStreamResult:
    events: List[str] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    text: str = ""
    done_payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def stream_chat(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    message: str,
    active_source_ids: Optional[List[str]] = None,
    chat_id: Optional[str] = None,
    notebook_id: Optional[str] = None,
    include_ncert_global: bool = False,
    ncert_class: Optional[int] = None,
    ncert_subject: Optional[str] = None,
    ncert_chapter_no: Optional[int] = None,
    ncert_chapter_name: Optional[str] = None,
    ncert_concept: Optional[str] = None,
    timeout: float = 180.0,
) -> ChatStreamResult:
    payload: Dict[str, Any] = {
        "message": message,
        "history": [],
        "active_source_ids": list(active_source_ids or []),
    }
    if chat_id:
        payload["chat_id"] = chat_id
    if notebook_id:
        payload["notebook_id"] = notebook_id
    if include_ncert_global:
        payload["include_ncert_global"] = True
    if ncert_class is not None:
        payload["ncert_class"] = ncert_class
    if ncert_subject is not None:
        payload["ncert_subject"] = ncert_subject
    if ncert_chapter_no is not None:
        payload["ncert_chapter_no"] = ncert_chapter_no
    if ncert_chapter_name is not None:
        payload["ncert_chapter_name"] = ncert_chapter_name
    if ncert_concept is not None:
        payload["ncert_concept"] = ncert_concept

    result = ChatStreamResult()
    current_event: Optional[str] = None

    try:
        with client.stream(
            "POST",
            f"{base_url}/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
            json=payload,
            timeout=timeout,
        ) as response:
            if response.status_code >= 400:
                result.error = f"HTTP {response.status_code}: {response.read().decode(errors='replace')[:300]}"
                return result
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line.split("event:", 1)[1].strip()
                    result.events.append(current_event)
                elif line.startswith("data:") and current_event:
                    data_str = line.split("data:", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        data = None
                    if current_event == "citation" and isinstance(data, dict):
                        result.citations.append(data)
                    elif current_event == "chunk" and isinstance(data, dict):
                        result.text += data.get("text", "")
                    elif current_event == "done" and isinstance(data, dict):
                        result.done_payload = data
                    elif current_event == "error":
                        result.error = data_str
                        break
    except httpx.HTTPError as exc:
        result.error = str(exc)
    return result
