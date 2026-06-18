"""Shared helpers for TestSprite cloud-executed API tests."""

from __future__ import annotations

import base64
import io
import json
import time
from typing import Any, Dict, List, Optional

import requests

from fixture_payloads import FIXTURES

BASE_URL = "http://localhost:8000"
TIMEOUT = 120
POLL_INTERVAL = 2
MAX_POLL_SECONDS = 300


def dev_jwt(sub: str = "testsprite_user") -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}."


def auth_headers(sub: str = "testsprite_user") -> Dict[str, str]:
    return {"Authorization": f"Bearer {dev_jwt(sub)}"}


def fixture_bytes(name: str) -> bytes:
    if name not in FIXTURES:
        raise KeyError(f"Unknown fixture: {name}")
    return base64.b64decode(FIXTURES[name])


def upload_bytes(
    filename: str,
    content: bytes,
    content_type: str,
    *,
    sub: str = "testsprite_user",
    pdf_password: Optional[str] = None,
) -> Dict[str, Any]:
    headers = auth_headers(sub)
    data: Dict[str, str] = {}
    if pdf_password:
        data["pdf_password"] = pdf_password
    files = {"file": (filename, io.BytesIO(content), content_type)}
    response = requests.post(
        f"{BASE_URL}/api/v1/ingest/upload",
        headers=headers,
        files=files,
        data=data,
        timeout=TIMEOUT,
    )
    return {"status_code": response.status_code, "body": response.json() if response.content else {}, "text": response.text}


def upload_fixture(name: str, *, sub: str = "testsprite_user", pdf_password: Optional[str] = None) -> Dict[str, Any]:
    content = fixture_bytes(name)
    if name.endswith(".pdf"):
        ctype = "application/pdf"
    else:
        ctype = "text/plain"
    return upload_bytes(name, content, ctype, sub=sub, pdf_password=pdf_password)


def wait_indexed(source_id: str, *, sub: str = "testsprite_user") -> Dict[str, Any]:
    headers = auth_headers(sub)
    deadline = time.time() + MAX_POLL_SECONDS
    last = None
    while time.time() < deadline:
        response = requests.get(f"{BASE_URL}/api/v1/ingest/sources", headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        sources = response.json().get("sources", [])
        last = next((s for s in sources if s.get("id") == source_id), None)
        if last and last.get("status") == "indexed":
            return last
        if last and last.get("status") == "error":
            return last
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Source {source_id} not indexed. Last={last}")


def stream_chat(message: str, source_ids: List[str], *, sub: str = "testsprite_user") -> Dict[str, Any]:
    headers = {**auth_headers(sub), "Accept": "text/event-stream"}
    payload = {"message": message, "history": [], "active_source_ids": source_ids}
    response = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        headers=headers,
        json=payload,
        timeout=TIMEOUT,
        stream=True,
    )
    events: List[str] = []
    citations: List[Dict[str, Any]] = []
    text = ""
    if response.status_code != 200:
        return {"status_code": response.status_code, "text": response.text, "events": events, "citations": citations}
    current = None
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            current = line.split("event:", 1)[1].strip()
            events.append(current)
        elif line.startswith("data:") and current:
            data_str = line.split("data:", 1)[1].strip()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = None
            if current == "citation" and isinstance(data, dict):
                citations.append(data)
            elif current == "chunk" and isinstance(data, dict):
                text += data.get("text", "")
    return {"status_code": 200, "events": events, "citations": citations, "text": text}
