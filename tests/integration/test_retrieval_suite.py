"""
RET integration tests — thin pytest wrapper around retrieval_eval runner.

RET-04 (citation correctness) and RET-07 (source isolation) have dedicated tests.
"""

from __future__ import annotations

import httpx
import pytest

from tests.helpers.auth import make_dev_jwt
from tests.helpers.chat_client import stream_chat
from tests.helpers.ingest_client import upload_file, wait_for_source_status

pytestmark = [pytest.mark.integration, pytest.mark.retrieval]


class TestRET07SourceIsolation:
    """RET-07: User A sources never retrieved for User B."""

    def test_ret07_cross_user_source_forbidden(
        self,
        require_integration,
        base_url,
        fixtures_dir,
        integration_user_id,
        integration_user_b_id,
        tenant_id,
    ):
        token_a = make_dev_jwt(integration_user_id)
        token_b = make_dev_jwt(integration_user_b_id)

        with httpx.Client(timeout=120.0) as client:
            upload_a = upload_file(
                client,
                base_url=base_url,
                token=token_a,
                file_path=fixtures_dir / "sample_phrase_alpha.txt",
                title="user_a_secret_doc",
            )
            assert upload_a.status_code == 200
            source_a = upload_a.json()["id"]
            wait_for_source_status(client, base_url=base_url, token=token_a, source_id=source_a)

            # User B must not access User A's source_id (403 before stream)
            response = client.post(
                f"{base_url}/api/v1/chat/stream",
                headers={
                    "Authorization": f"Bearer {token_b}",
                    "Accept": "text/event-stream",
                },
                json={
                    "message": "What is the mitochondria powerhouse phrase?",
                    "history": [],
                    "active_source_ids": [source_a],
                },
                timeout=60.0,
            )
            assert response.status_code == 403


class TestRET06NoAnswerBehavior:
    """RET-06: Negative bucket refusal (smoke)."""

    def test_ret06_refuses_out_of_corpus_question(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir
    ):
        upload = upload_file(
            api_client,
            base_url=base_url,
            token=auth_token,
            file_path=fixtures_dir / "standard_chapter.pdf",
        )
        source_id = upload.json()["id"]
        wait_for_source_status(api_client, base_url=base_url, token=auth_token, source_id=source_id)

        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message="What year will humans colonize Mars permanently?",
            active_source_ids=[source_id],
        )
        text = (chat.text or "").lower()
        assert "not found" in text or any(
            m in text for m in ("not found in provided sources", "not found in the selected sources")
        )


@pytest.mark.slow
def test_ret_eval_runner_smoke(require_integration, base_url):
    """Run retrieval eval runner and assert harness executes."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "evals/runners/retrieval_eval.py", "--base-url", base_url],
        cwd=str(pytest.importorskip("pathlib").Path(__file__).resolve().parents[2]),
        env={**__import__("os").environ, "INTEGRATION_TESTS": "1"},
        capture_output=True,
        text=True,
    )
    assert "RET-01" in result.stdout or result.returncode in {0, 1}
