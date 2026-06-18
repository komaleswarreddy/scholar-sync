"""Timed chat/studio/ingest clients for PRF performance tests."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from tests.helpers.ingest_client import upload_file, wait_for_source_status
from tests.helpers.studio_client import generate_studio


@dataclass
class ChatTimingResult:
    ttft_ms: Optional[float] = None
    e2e_ms: Optional[float] = None
    error: Optional[str] = None
    http_status: Optional[int] = None
    text: str = ""
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[float] = None
    events: List[str] = field(default_factory=list)
    done_payload: Optional[Dict[str, Any]] = None


@dataclass
class StudioTimingResult:
    task_type: str = ""
    e2e_ms: Optional[float] = None
    status_code: int = 0
    error: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass
class IngestTimingResult:
    e2e_ms: Optional[float] = None
    source_id: Optional[str] = None
    error: Optional[str] = None
    http_status: Optional[int] = None


CHAT_QUESTIONS = [
    "What is photosynthesis?",
    "Explain the Calvin cycle briefly.",
    "What role does chlorophyll play?",
    "How do plants convert light energy?",
    "What are the reactants in photosynthesis?",
]


def stream_chat_timed(
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
) -> ChatTimingResult:
    """Measure TTFT (first chunk/citation) and E2E (done event) for chat SSE."""
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

    result = ChatTimingResult()
    current_event: Optional[str] = None
    t_start = time.perf_counter()
    first_token_at: Optional[float] = None

    try:
        with client.stream(
            "POST",
            f"{base_url}/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
            json=payload,
            timeout=timeout,
        ) as response:
            result.http_status = response.status_code
            if response.status_code >= 400:
                result.error = f"HTTP {response.status_code}: {response.read().decode(errors='replace')[:300]}"
                result.e2e_ms = (time.perf_counter() - t_start) * 1000
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
                    if current_event in ("chunk", "citation") and first_token_at is None:
                        first_token_at = time.perf_counter()
                        result.ttft_ms = (first_token_at - t_start) * 1000
                    if current_event == "chunk" and isinstance(data, dict):
                        result.text += data.get("text", "")
                    elif current_event == "done" and isinstance(data, dict):
                        result.done_payload = data
                        break
                    elif current_event == "error":
                        result.error = data_str
                        break
    except httpx.HTTPError as exc:
        result.error = str(exc)

    result.e2e_ms = (time.perf_counter() - t_start) * 1000
    if result.ttft_ms is None and not result.error:
        result.ttft_ms = result.e2e_ms

    if result.done_payload:
        usage = result.done_payload.get("usage") or {}
        if isinstance(usage, dict):
            result.tokens_in = usage.get("prompt_tokens") or usage.get("input_tokens")
            result.tokens_out = usage.get("completion_tokens") or usage.get("output_tokens")
        result.cost_usd = result.done_payload.get("cost_usd")

    return result


def generate_studio_timed(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    task_type: str,
    source_ids: Optional[List[str]] = None,
    **kwargs: Any,
) -> StudioTimingResult:
    t_start = time.perf_counter()
    gen = generate_studio(
        client,
        base_url=base_url,
        token=token,
        task_type=task_type,
        source_ids=source_ids,
        **kwargs,
    )
    e2e_ms = (time.perf_counter() - t_start) * 1000
    error = None
    if gen.status_code >= 400:
        error = gen.body.get("detail") or gen.raw_text[:200]
    return StudioTimingResult(
        task_type=task_type,
        e2e_ms=e2e_ms,
        status_code=gen.status_code,
        error=error,
        trace_id=gen.trace_id,
    )


def ingest_timed(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    file_path: Path,
    title: str = "prf_ingest_probe",
    timeout_s: float = 300.0,
) -> IngestTimingResult:
    t_start = time.perf_counter()
    result = IngestTimingResult()
    try:
        response = upload_file(client, base_url=base_url, token=token, file_path=file_path, title=title)
        result.http_status = response.status_code
        if response.status_code != 200:
            result.error = f"HTTP {response.status_code}: {response.text[:200]}"
            result.e2e_ms = (time.perf_counter() - t_start) * 1000
            return result
        source_id = response.json()["id"]
        result.source_id = source_id
        wait_for_source_status(
            client,
            base_url=base_url,
            token=token,
            source_id=source_id,
            timeout_s=timeout_s,
        )
        result.e2e_ms = (time.perf_counter() - t_start) * 1000
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)
        result.e2e_ms = (time.perf_counter() - t_start) * 1000
    return result
