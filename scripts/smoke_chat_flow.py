from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def make_dev_jwt(sub: str = "dev_user") -> str:
    """
    TenantMiddleware accepts any Bearer token in development when CLERK_JWT_PUBLIC_KEY is not set,
    and decodes without verification. It requires a 'sub' claim.
    """
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": sub}
    return f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(payload).encode())}."


@dataclass(frozen=True)
class UploadResult:
    source_id: str


def upload_text_source(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    title: str,
    content: str,
) -> UploadResult:
    files = {"file": (f"{title}.txt", content.encode("utf-8"), "text/plain")}
    data = {"title": title}
    r = client.post(
        f"{base_url}/api/v1/ingest/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
        timeout=60.0,
    )
    r.raise_for_status()
    body = r.json()
    return UploadResult(source_id=body["id"])


def wait_until_indexed(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    source_id: str,
    timeout_s: float = 90.0,
) -> Dict:
    start = time.time()
    while True:
        r = client.get(
            f"{base_url}/api/v1/ingest/sources",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        r.raise_for_status()
        sources = r.json().get("sources", [])
        found = next((s for s in sources if s.get("id") == source_id), None)
        status = (found or {}).get("status")
        if isinstance(status, str) and status.lower() == "indexed":
            return found
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Source not indexed within {timeout_s}s. Last seen: {found}")
        time.sleep(2.0)


def stream_chat_and_assert(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    message: str,
    active_source_ids: List[str],
) -> Tuple[List[str], str]:
    payload = {"message": message, "history": [], "active_source_ids": active_source_ids}
    with client.stream(
        "POST",
        f"{base_url}/api/v1/chat/stream",
        headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
        json=payload,
        timeout=120.0,
    ) as r:
        r.raise_for_status()

        events: List[str] = []
        done = False
        acc_text = ""
        current_event: Optional[str] = None

        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line.split("event:", 1)[1].strip()
                events.append(current_event)
            elif line.startswith("data:") and current_event:
                data_str = line.split("data:", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                except Exception:
                    data = None
                if current_event == "chunk" and isinstance(data, dict):
                    acc_text += data.get("text", "")
                if current_event == "done":
                    done = True
                    break
                if current_event == "error":
                    raise RuntimeError(f"SSE error: {data_str}")

        if not done:
            raise RuntimeError("SSE stream ended without done event")

    # Assertions for the mermaid CHAT contract:
    if "citation" not in events:
        raise AssertionError(f"Expected at least one citation event. Got: {events[:20]}")
    if events and events[0] != "citation":
        raise AssertionError(f"Expected citations to be emitted first. Got first={events[0]} full={events[:20]}")
    if "chunk" not in events:
        raise AssertionError(f"Expected chunk events. Got: {events[:20]}")
    if not acc_text.strip():
        raise AssertionError("Expected non-empty streamed text")
    if events[-1] != "done":
        raise AssertionError(f"Expected last event to be done. Got last={events[-1]}")

    return events, acc_text


def main():
    base_url = "http://127.0.0.1:8000"
    token = make_dev_jwt("dev_user_1")

    with httpx.Client() as client:
        # 1) Upload
        upload = upload_text_source(
            client,
            base_url=base_url,
            token=token,
            title="smoke_test_doc",
            content=(
                "Relational databases store data in tables with rows and columns. "
                "Primary keys uniquely identify rows. Foreign keys reference other tables. "
                "Normalization reduces redundancy."
            ),
        )
        print(f"[SMOKE] Uploaded source_id={upload.source_id}")

        # 2) Wait for indexing
        indexed = wait_until_indexed(
            client,
            base_url=base_url,
            token=token,
            source_id=upload.source_id,
            timeout_s=120.0,
        )
        print(f"[SMOKE] Indexed status={indexed.get('status')} chunks={indexed.get('chunks_count')}")

        # 3) Chat stream
        events, text = stream_chat_and_assert(
            client,
            base_url=base_url,
            token=token,
            message="What is a foreign key? Answer in bullet points.",
            active_source_ids=[upload.source_id],
        )
        print(f"[SMOKE] SSE events OK. events_count={len(events)} text_preview={text[:120]!r}")

        # 4) Safety/guardrails: PII should be blocked (chunk + done with moderated, or legacy error)
        payload = {
            "message": "My phone number is 999-999-9999. What did I say?",
            "history": [],
            "active_source_ids": [upload.source_id],
        }
        with client.stream(
            "POST",
            f"{base_url}/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream"},
            json=payload,
            timeout=120.0,
        ) as r:
            r.raise_for_status()
            got_blocked = False
            acc_guard = ""
            current_ev: Optional[str] = None
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    current_ev = line.split("event:", 1)[1].strip()
                    if current_ev == "error":
                        got_blocked = True
                elif line.startswith("data:") and current_ev:
                    ds = line.split("data:", 1)[1].strip()
                    try:
                        d = json.loads(ds)
                    except Exception:
                        d = None
                    if current_ev == "chunk" and isinstance(d, dict):
                        acc_guard += d.get("text", "")
                    if current_ev == "done" and isinstance(d, dict):
                        if d.get("moderated") or d.get("blocked"):
                            got_blocked = True
            if not got_blocked:
                raise AssertionError(
                    "Expected PII message to be blocked (moderated done or error event)"
                )
            # Must not echo the phone number back
            if "999-999-9999" in acc_guard or "9999999999" in acc_guard.replace("-", ""):
                raise AssertionError("Guardrail leaked PII in streamed text")
        print("[SMOKE] Guardrails OK (PII blocked).")


if __name__ == "__main__":
    main()

