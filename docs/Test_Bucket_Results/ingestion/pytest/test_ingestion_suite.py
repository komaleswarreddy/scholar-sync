"""
ING-01 through ING-11 ingestion integration tests.

Requires:
  INTEGRATION_TESTS=1
  Running API (NOTEBOOKLM_API_URL, default http://127.0.0.1:8000)
  OPENAI_API_KEY, PINECONE_API_KEY, DATABASE_URL, storage configured

Generate fixtures first:
  python scripts/generate_test_fixtures.py
"""

from __future__ import annotations

import concurrent.futures
import statistics
import time
import uuid
from pathlib import Path

import httpx
import pytest

from tests.helpers.chat_client import stream_chat
from tests.helpers.ingest_client import (
    READY_STATUS,
    list_sources,
    upload_bytes,
    upload_file,
    wait_for_source_status,
)
from tests.helpers.pinecone_helpers import chunk_texts, fetch_source_chunks

pytestmark = [pytest.mark.integration, pytest.mark.ingestion]


class TestING01HappyPathPdfUpload:
    """ING-01: Happy-path PDF upload."""

    def test_ing01_pdf_upload_indexed_with_retrievable_chunks(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir, tenant_id
    ):
        response = upload_file(
            api_client, base_url=base_url, token=auth_token, file_path=fixtures_dir / "standard_chapter.pdf"
        )
        assert response.status_code == 200, response.text
        body = response.json()
        source_id = body["id"]
        assert body["status"] == "processing"

        final = wait_for_source_status(
            api_client, base_url=base_url, token=auth_token, source_id=source_id, timeout_s=180.0
        )
        assert final["status"] == READY_STATUS
        assert int(final.get("chunks_count") or 0) > 0

        chunks = fetch_source_chunks(tenant_id=tenant_id, source_id=source_id)
        assert chunks, "Expected chunks in Pinecone"
        texts = " ".join(chunk_texts(chunks)).lower()
        assert "photosynthesis" in texts or "chlorophyll" in texts

        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message="What is photosynthesis?",
            active_source_ids=[source_id],
        )
        assert chat.citations, "Expected citation events in chat stream"
        citation_blob = " ".join(
            (c.get("text") or "") for c in chat.citations[:3]
        ).lower()
        assert "photosynthesis" in citation_blob or "chlorophyll" in citation_blob, (
            "Top retrieved citations should include expected chapter phrases"
        )


class TestING02TxtUpload:
    """ING-02: TXT upload (DOCX skipped per project decision)."""

    def test_ing02_txt_phrases_indexed(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir, tenant_id
    ):
        for name, phrase in [
            ("sample_phrase_alpha.txt", "ING02_ALPHA_PHRASE"),
            ("sample_phrase_beta.txt", "ING02_BETA_PHRASE"),
        ]:
            response = upload_file(
                api_client, base_url=base_url, token=auth_token, file_path=fixtures_dir / name
            )
            assert response.status_code == 200, response.text
            source_id = response.json()["id"]
            final = wait_for_source_status(
                api_client, base_url=base_url, token=auth_token, source_id=source_id
            )
            assert final["status"] == READY_STATUS
            chunks = fetch_source_chunks(tenant_id=tenant_id, source_id=source_id)
            assert any(phrase in t for t in chunk_texts(chunks))

    @pytest.mark.skip(reason="DOCX not supported; ING-02 DOCX portion blocked by design")
    def test_ing02_docx_blocked(self):
        pass


class TestING03EncryptedPdf:
    """ING-03: Encrypted PDF with password."""

    def test_ing03_encrypted_without_password_rejected_sync(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir
    ):
        response = upload_file(
            api_client,
            base_url=base_url,
            token=auth_token,
            file_path=fixtures_dir / "encrypted_sample.pdf",
        )
        assert response.status_code == 400
        assert "password" in response.json().get("detail", "").lower()

    def test_ing03_encrypted_with_password_indexes(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir, tenant_id
    ):
        response = upload_file(
            api_client,
            base_url=base_url,
            token=auth_token,
            file_path=fixtures_dir / "encrypted_sample.pdf",
            pdf_password="testpass",
        )
        assert response.status_code == 200, response.text
        source_id = response.json()["id"]
        final = wait_for_source_status(
            api_client, base_url=base_url, token=auth_token, source_id=source_id
        )
        assert final["status"] == READY_STATUS
        chunks = fetch_source_chunks(tenant_id=tenant_id, source_id=source_id)
        assert chunks


class TestING04LargeFile:
    """ING-04: Large file processing (synthetic 50-page; scale to 100+ in staging)."""

    @pytest.mark.slow
    def test_ing04_large_pdf_completes_within_sla(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir, tenant_id
    ):
        start = time.time()
        response = upload_file(
            api_client, base_url=base_url, token=auth_token, file_path=fixtures_dir / "large_50page.pdf"
        )
        assert response.status_code == 200
        source_id = response.json()["id"]
        final = wait_for_source_status(
            api_client, base_url=base_url, token=auth_token, source_id=source_id, timeout_s=300.0
        )
        elapsed = time.time() - start
        assert final["status"] == READY_STATUS
        # Staging target: <5 min for 200 pages; synthetic 50-page budget 120s
        assert elapsed < 120.0, f"Large PDF took {elapsed:.1f}s"
        chunks = fetch_source_chunks(tenant_id=tenant_id, source_id=source_id, top_k=200)
        assert chunks, "Expected indexed chunks for large PDF"
        texts = " ".join(chunk_texts(chunks))
        assert "Large document page 50" in texts, "Large PDF content should be retrievable"


class TestING05CorruptedFileFailure:
    """ING-05: Corrupted / fake PDF graceful failure."""

    @pytest.mark.parametrize(
        "filename",
        ["truncated.pdf", "jpg_renamed.pdf"],
    )
    def test_ing05_invalid_pdfs_rejected(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir, filename
    ):
        response = upload_file(
            api_client, base_url=base_url, token=auth_token, file_path=fixtures_dir / filename
        )
        assert response.status_code == 400
        assert response.status_code < 500

    def test_ing05_empty_file_rejected(self, require_integration, api_client, base_url, auth_token):
        response = upload_bytes(
            api_client,
            base_url=base_url,
            token=auth_token,
            filename="empty.pdf",
            content=b"",
            content_type="application/pdf",
        )
        assert response.status_code == 400


class TestING06UnsupportedFileType:
    """ING-06: Unsupported file type rejection."""

    @pytest.mark.parametrize("filename,content", [("malware.exe", b"MZ"), ("video.mp4", b"\x00\x00\x00\x20ftyp"), ("archive.zip", b"PK\x03\x04")])
    def test_ing06_blocked_extensions(
        self, require_integration, api_client, base_url, auth_token, filename, content
    ):
        response = upload_bytes(
            api_client,
            base_url=base_url,
            token=auth_token,
            filename=filename,
            content=content,
            content_type="application/octet-stream",
        )
        assert response.status_code == 400
        assert response.status_code < 500


class TestING07DuplicateUpload:
    """ING-07: Duplicate upload handling."""

    def test_ing07_duplicate_upload_creates_distinct_sources(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir, tenant_id
    ):
        path = fixtures_dir / "sample_phrase_alpha.txt"
        ids = []
        for _ in range(2):
            response = upload_file(api_client, base_url=base_url, token=auth_token, file_path=path)
            assert response.status_code == 200
            ids.append(response.json()["id"])
        assert ids[0] != ids[1]
        for source_id in ids:
            final = wait_for_source_status(
                api_client, base_url=base_url, token=auth_token, source_id=source_id
            )
            assert final["status"] == READY_STATUS


class TestING08ChunkingQuality:
    """ING-08: Manual rubric — automated sampling only; see scripts/rubric_ing08_chunk_quality.py."""

    def test_ing08_chunk_sample_export_available(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir, tenant_id
    ):
        response = upload_file(
            api_client, base_url=base_url, token=auth_token, file_path=fixtures_dir / "standard_chapter.pdf"
        )
        source_id = response.json()["id"]
        wait_for_source_status(api_client, base_url=base_url, token=auth_token, source_id=source_id)
        chunks = fetch_source_chunks(tenant_id=tenant_id, source_id=source_id)
        assert chunks, "No chunks to sample for ING-08 rubric"


class TestING09ScannedPdf:
    """ING-09: Scanned / image-only PDF handling."""

    def test_ing09_blank_pdf_fails_with_clear_message(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir
    ):
        response = upload_file(
            api_client, base_url=base_url, token=auth_token, file_path=fixtures_dir / "blank_scanned.pdf"
        )
        assert response.status_code == 200
        source_id = response.json()["id"]
        final = wait_for_source_status(
            api_client,
            base_url=base_url,
            token=auth_token,
            source_id=source_id,
            target_statuses=["error", READY_STATUS],
        )
        if final["status"] == "error":
            msg = (final.get("error_message") or "").lower()
            assert "image-only" in msg or "no extractable text" in msg
        else:
            pytest.fail("Blank scanned PDF should not reach indexed without OCR")


class TestING10PipelineLatency:
    """ING-10: Pipeline latency SLA (synthetic subset)."""

    @pytest.mark.slow
    def test_ing10_small_pdf_latency_budget(
        self, require_integration, api_client, base_url, auth_token, fixtures_dir
    ):
        durations = []
        for i in range(3):
            unique = fixtures_dir / f"_latency_{uuid.uuid4().hex}.txt"
            unique.write_text(f"Latency probe {i}: unique content {uuid.uuid4()}\n", encoding="utf-8")
            try:
                start = time.time()
                response = upload_file(api_client, base_url=base_url, token=auth_token, file_path=unique)
                assert response.status_code == 200
                source_id = response.json()["id"]
                wait_for_source_status(
                    api_client, base_url=base_url, token=auth_token, source_id=source_id, timeout_s=90.0
                )
                durations.append(time.time() - start)
            finally:
                unique.unlink(missing_ok=True)
        p95 = statistics.quantiles(durations, n=20)[-1] if len(durations) > 1 else durations[0]
        assert p95 < 90.0, f"P95 latency {p95:.1f}s exceeds 90s budget for small docs"


class TestING11ConcurrentUploads:
    """ING-11: Concurrent uploads."""

    @pytest.mark.slow
    def test_ing11_concurrent_uploads_all_index(
        self, require_integration, base_url, auth_token, fixtures_dir
    ):
        def _one_upload(idx: int) -> str:
            token = auth_token
            with httpx.Client(timeout=120.0) as client:
                unique = fixtures_dir / f"_concurrent_{uuid.uuid4().hex}.txt"
                unique.write_text(f"Concurrent upload {idx}: {uuid.uuid4()}\n", encoding="utf-8")
                try:
                    response = upload_file(client, base_url=base_url, token=token, file_path=unique)
                    response.raise_for_status()
                    source_id = response.json()["id"]
                    final = wait_for_source_status(
                        client, base_url=base_url, token=token, source_id=source_id, timeout_s=180.0
                    )
                    assert final["status"] == READY_STATUS
                    return source_id
                finally:
                    unique.unlink(missing_ok=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_one_upload, i) for i in range(5)]
            results = [f.result() for f in futures]
        assert len(set(results)) == 5
