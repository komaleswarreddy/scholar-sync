"""HTTP helpers for IPI (indirect injection) integration tests."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from tests.helpers.ingest_client import upload_file, wait_for_source_status
from tests.helpers.studio_client import generate_studio
from tests.helpers.guardrails_client import stream_guardrail_check


def upload_ipi_fixture(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    fixture_path: Path,
    title_prefix: str = "ipi_test",
) -> str:
    title = f"{title_prefix}_{uuid.uuid4().hex[:8]}_{fixture_path.stem}"
    resp = upload_file(
        client,
        base_url=base_url,
        token=token,
        file_path=fixture_path,
        title=title,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"IPI upload failed {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    source_id = body.get("source_id") or body.get("id")
    if not source_id:
        raise RuntimeError(f"IPI upload missing source_id: {body}")
    final = wait_for_source_status(
        client,
        base_url=base_url,
        token=token,
        source_id=source_id,
        timeout_s=240.0,
    )
    if (final.get("status") or "").lower() == "error":
        raise RuntimeError(f"IPI source index error: {final}")
    return str(source_id)


def ipi_chat(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    message: str,
    active_source_ids: Optional[List[str]] = None,
) -> str:
    result = stream_guardrail_check(
        client,
        base_url=base_url,
        token=token,
        message=message,
        active_source_ids=list(active_source_ids or []),
    )
    if result.error and "HTTP 5" in result.error:
        raise RuntimeError(result.error)
    return result.text or ""


def ipi_studio_quiz(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    source_ids: List[str],
) -> Dict[str, Any]:
    result = generate_studio(
        client,
        base_url=base_url,
        token=token,
        task_type="quiz",
        source_ids=source_ids,
        timeout=300.0,
    )
    if result.status_code >= 500:
        raise RuntimeError(f"Studio HTTP {result.status_code}: {result.raw_text[:300]}")
    return result.body
