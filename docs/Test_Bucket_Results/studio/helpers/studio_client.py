"""Studio generate API helpers for integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx


@dataclass
class StudioGenerateResult:
    status_code: int
    body: Dict[str, Any]
    trace_id: Optional[str] = None
    raw_text: str = ""


def generate_studio(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    task_type: str,
    source_ids: Optional[List[str]] = None,
    context_mode: str = "sources_only",
    custom_instructions: Optional[str] = None,
    retrieval_focus: Optional[str] = None,
    report_format: Optional[str] = None,
    chat_transcript: Optional[str] = None,
    selection_text: Optional[str] = None,
    include_ncert_global: bool = False,
    ncert_class: Optional[int] = None,
    ncert_subject: Optional[str] = None,
    ncert_chapter_no: Optional[int] = None,
    ncert_chapter_name: Optional[str] = None,
    timeout: float = 300.0,
) -> StudioGenerateResult:
    payload: Dict[str, Any] = {
        "task_type": task_type,
        "source_ids": list(source_ids or []),
        "context_mode": context_mode,
    }
    if custom_instructions is not None:
        payload["custom_instructions"] = custom_instructions
    if retrieval_focus is not None:
        payload["retrieval_focus"] = retrieval_focus
    if report_format is not None:
        payload["report_format"] = report_format
    if chat_transcript is not None:
        payload["chat_transcript"] = chat_transcript
    if selection_text is not None:
        payload["selection_text"] = selection_text
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

    response = client.post(
        f"{base_url}/api/v1/studio/generate",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=timeout,
    )
    raw_text = response.text
    body: Dict[str, Any] = {}
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                body = parsed
        except Exception:
            body = {}
    trace_id = body.get("trace_id")
    return StudioGenerateResult(
        status_code=response.status_code,
        body=body,
        trace_id=trace_id if isinstance(trace_id, str) else None,
        raw_text=raw_text,
    )
