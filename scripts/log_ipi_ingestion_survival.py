#!/usr/bin/env python3
"""
Upload IPI fixtures and log whether poison payloads survive ingestion into chunks.

Usage:
  INTEGRATION_TESTS=1 python scripts/log_ipi_ingestion_survival.py
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tests.helpers.auth import make_dev_jwt  # noqa: E402
from tests.helpers.ingest_client import upload_file, wait_for_source_status  # noqa: E402
from tests.helpers.pinecone_helpers import chunk_texts, fetch_source_chunks  # noqa: E402

IPI_DIR = ROOT / "tests" / "fixtures" / "ipi"
MANIFEST = IPI_DIR / "manifest.json"
REPORT = ROOT / "evals" / "reports" / "ipi_ingestion_survival.json"
TENANT_ID = os.getenv("NOTEBOOKLM_TENANT_ID", "eeff7c1c-fe22-4573-ad93-a36f19ad4dc5")
BASE_URL = os.getenv("NOTEBOOKLM_API_URL", "http://127.0.0.1:8000")

PAYLOAD_MARKERS = {
    "ignore previous instructions",
    "reveal the system prompt",
    "19.8 m/s",
    "complete exam answers regardless of policy",
    "aWdub3JlIHByZXZpb3Vz",
}


def _payload_survives(texts: list[str], fixture: dict) -> bool:
    joined = " ".join(texts).lower()
    preview = (fixture.get("payload_preview") or "").lower()
    if preview and any(tok in joined for tok in preview.split()[:4] if len(tok) > 4):
        return True
    return any(marker in joined for marker in PAYLOAD_MARKERS)


def main() -> int:
    if not MANIFEST.exists():
        print("Run scripts/generate_ipi_fixtures.py first")
        return 2
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fixtures = manifest.get("fixtures") or []
    token = make_dev_jwt("ipi_survival_runner")
    results: list[dict] = []

    with httpx.Client(base_url=BASE_URL, timeout=180.0) as client:
        client.headers["Authorization"] = f"Bearer {token}"
        health = client.get("/health")
        if health.status_code != 200:
            print(f"API unhealthy: {health.status_code}")
            return 2

        for fx in fixtures:
            file_name = fx.get("file")
            path = IPI_DIR / str(file_name)
            if not path.exists():
                results.append({"file": file_name, "error": "missing_fixture"})
                continue
            title = f"ipi_survival_{uuid.uuid4().hex[:8]}_{path.stem}"
            resp = upload_file(
                client,
                base_url=BASE_URL,
                token=token,
                file_path=path,
                title=title,
            )
            if resp.status_code >= 400:
                results.append(
                    {
                        "file": file_name,
                        "hiding_method": fx.get("hiding_method"),
                        "error": f"upload_http_{resp.status_code}",
                    }
                )
                continue
            body = resp.json()
            source_id = body.get("source_id") or body.get("id")
            try:
                final = wait_for_source_status(
                    client,
                    base_url=BASE_URL,
                    token=token,
                    source_id=source_id,
                    timeout_s=240.0,
                )
            except TimeoutError as exc:
                results.append(
                    {
                        "file": file_name,
                        "source_id": source_id,
                        "error": str(exc),
                    }
                )
                continue

            status = (final.get("status") or "").lower()
            if status == "error":
                results.append(
                    {
                        "file": file_name,
                        "source_id": source_id,
                        "error": final.get("error_message") or "index_error",
                    }
                )
                continue

            chunks = fetch_source_chunks(tenant_id=TENANT_ID, source_id=source_id)
            texts = chunk_texts(chunks)
            survives = _payload_survives(texts, fx)
            preview = (texts[0][:240] if texts else "")
            results.append(
                {
                    "file": file_name,
                    "test_ids": fx.get("test_ids"),
                    "hiding_method": fx.get("hiding_method"),
                    "source_id": source_id,
                    "chunks_count": len(chunks),
                    "payload_survives_ingestion": survives,
                    "chunk_preview": preview,
                    "defense_note": (
                        "parser-stripped"
                        if not survives
                        else "payload_reached_chunks"
                    ),
                }
            )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {
                "manifest_version": manifest.get("version"),
                "fixtures": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {REPORT} ({len(results)} fixtures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
