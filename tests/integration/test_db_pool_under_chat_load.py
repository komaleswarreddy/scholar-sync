"""
Concurrent chat streams should not exhaust the DB pool (short-lived sessions per node).

Requires INTEGRATION_TESTS=1 and a running API with indexed standard_chapter.
"""

from __future__ import annotations

import concurrent.futures
import uuid

import httpx
import pytest

from tests.helpers.auth import make_dev_jwt
from tests.helpers.chat_client import stream_chat
from tests.helpers.ingest_client import upload_file, wait_for_source_status


@pytest.mark.integration
@pytest.mark.slow
def test_concurrent_chat_streams_no_pool_exhaustion(
    require_integration,
    api_client: httpx.Client,
    base_url: str,
    auth_token: str,
    fixtures_dir,
) -> None:
    """Fire several parallel SSE chats; expect no 5xx / pool timeout errors."""
    resp = upload_file(
        api_client,
        base_url=base_url,
        token=auth_token,
        file_path=fixtures_dir / "standard_chapter.pdf",
        title=f"pool_load_{uuid.uuid4().hex[:8]}",
    )
    assert resp.status_code == 200, resp.text
    source_id = resp.json()["id"]
    wait_for_source_status(
        api_client, base_url=base_url, token=auth_token, source_id=source_id
    )

    questions = [
        "What is photosynthesis?",
        "Explain chlorophyll.",
        "What is the Calvin cycle?",
        "How do plants store energy?",
        "What are stomata?",
        "Describe light reactions.",
    ]

    def one_chat(q: str) -> None:
        token = make_dev_jwt(f"pool_chat_{uuid.uuid4().hex[:8]}")
        with httpx.Client(timeout=180.0) as client:
            chat = stream_chat(
                client,
                base_url=base_url,
                token=token,
                message=q,
                active_source_ids=[source_id],
            )
        assert chat.text, "expected non-empty answer"

    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(one_chat, q) for q in questions]
        for fut in concurrent.futures.as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                errors.append(msg)
                if "MaxClientsInSessionMode" in msg or "pool" in msg.lower():
                    pytest.fail(f"DB pool exhaustion: {msg}")

    assert not errors, f"concurrent chat failures: {errors[:3]}"
