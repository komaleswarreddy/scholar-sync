"""HTTP helpers for ingestion integration tests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

READY_STATUS = "indexed"


@dataclass
class UploadResult:
    source_id: str
    status: str
    raw: Dict[str, Any]


def upload_file(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    file_path: Path,
    title: Optional[str] = None,
    pdf_password: Optional[str] = None,
) -> httpx.Response:
    content_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "text/plain"
    data: Dict[str, str] = {"title": title or file_path.stem}
    if pdf_password:
        data["pdf_password"] = pdf_password
    with file_path.open("rb") as fh:
        files = {"file": (file_path.name, fh, content_type)}
        return client.post(
            f"{base_url}/api/v1/ingest/upload",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data,
            timeout=120.0,
        )


def upload_bytes(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    filename: str,
    content: bytes,
    content_type: str,
    title: Optional[str] = None,
    pdf_password: Optional[str] = None,
) -> httpx.Response:
    data: Dict[str, str] = {"title": title or Path(filename).stem}
    if pdf_password:
        data["pdf_password"] = pdf_password
    files = {"file": (filename, content, content_type)}
    return client.post(
        f"{base_url}/api/v1/ingest/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
        timeout=120.0,
    )


def list_sources(client: httpx.Client, *, base_url: str, token: str) -> List[Dict[str, Any]]:
    response = client.get(
        f"{base_url}/api/v1/ingest/sources",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json().get("sources", [])


def wait_for_source_status(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    source_id: str,
    target_statuses: Optional[List[str]] = None,
    timeout_s: float = 180.0,
    poll_s: float = 2.0,
) -> Dict[str, Any]:
    targets = {s.lower() for s in (target_statuses or [READY_STATUS, "error"])}
    start = time.time()
    last: Optional[Dict[str, Any]] = None
    while time.time() - start < timeout_s:
        try:
            sources = list_sources(client, base_url=base_url, token=token)
        except httpx.HTTPError:
            time.sleep(poll_s)
            continue
        last = next((s for s in sources if s.get("id") == source_id), None)
        status = (last or {}).get("status", "").lower()
        if status in targets:
            return last or {}
        time.sleep(poll_s)
    raise TimeoutError(f"Source {source_id} not in {targets} within {timeout_s}s. Last={last}")
