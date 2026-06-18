"""
Archive excerpt from tests/conftest.py — NBM-specific fixtures and leak-probe loader.

Canonical live copy: tests/conftest.py (merged with ING/RET fixtures).
Run tests from repo root, not from this archive path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Tuple

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
NBM_LEAK_PROBE_PATH = ROOT / "evals" / "datasets" / "nbm_leak_probe.json"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "ingestion"

NBM_LEAK_PROBE_FALLBACK: List[Tuple[str, List[str]]] = [
    ("What is the capital of France?", ["paris"]),
    ("What is g in m/s² on Earth?", ["9.8", "9.81"]),
    ("What gas do plants absorb for photosynthesis?", ["carbon dioxide", "co2"]),
]


def load_nbm_leak_probe() -> List[Tuple[str, List[str]]]:
    if not NBM_LEAK_PROBE_PATH.exists():
        return list(NBM_LEAK_PROBE_FALLBACK)
    data = json.loads(NBM_LEAK_PROBE_PATH.read_text(encoding="utf-8"))
    items = data.get("items") or []
    return [
        (item["question"], list(item.get("forbidden_answer_substrings") or []))
        for item in items
        if item.get("question")
    ]


# Registered in pytest_configure (tests/conftest.py):
# config.addinivalue_line("markers", "notebook_mode: notebook-mode guardrail tests (NBM-*)")
# Registered in pyproject.toml markers list.


@pytest.fixture(scope="session")
def nbm_leak_probe_questions():
    questions = load_nbm_leak_probe()
    if not questions:
        pytest.skip(f"No leak-probe items in {NBM_LEAK_PROBE_PATH}")
    return questions


def _require_integration_session(base_url: str) -> None:
    if os.getenv("INTEGRATION_TESTS", "").strip() not in {"1", "true", "yes"}:
        pytest.skip("Set INTEGRATION_TESTS=1 to run live integration tests")
    if not (os.getenv("OPENAI_API_KEY") and os.getenv("PINECONE_API_KEY")):
        pytest.skip("OPENAI_API_KEY and PINECONE_API_KEY required for integration tests")
    try:
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.get(f"{base_url}/health")
        if response.status_code != 200:
            pytest.skip(f"API not healthy at {base_url}: {response.status_code}")
    except httpx.HTTPError as exc:
        pytest.skip(f"API unreachable at {base_url}: {exc}")


@pytest.fixture(scope="session")
def nbm_exploratory_source_id(base_url, fixtures_dir):
    """Upload a narrow source once for exploratory NBM tests."""
    _require_integration_session(base_url)
    if not FIXTURES_DIR.exists():
        pytest.skip("Run scripts/generate_test_fixtures.py first")

    from tests.helpers.auth import make_dev_jwt
    from tests.helpers.ingest_client import upload_file, wait_for_source_status

    token = make_dev_jwt("ing_test_user_a")
    with httpx.Client(base_url=base_url, timeout=120.0) as client:
        upload = upload_file(
            client,
            base_url=base_url,
            token=token,
            file_path=fixtures_dir / "sample_phrase_alpha.txt",
            title="nbm_leak_probe_source",
        )
        if upload.status_code >= 500:
            pytest.skip(f"[infra-error] upload failed: {upload.status_code}")
        upload.raise_for_status()
        source_id = upload.json()["id"]
        wait_for_source_status(client, base_url=base_url, token=token, source_id=source_id)
        return source_id


@pytest.fixture(scope="session")
def nbm_tutor_scope(base_url):
    """Resolve a seeded NCERT chapter scope from tutor catalog."""
    _require_integration_session(base_url)
    from tests.helpers.auth import make_dev_jwt

    class_num = int(os.getenv("NBM_TUTOR_CLASS", "10"))
    subject_key = os.getenv("NBM_TUTOR_SUBJECT", "science")
    chapter_override = os.getenv("NBM_TUTOR_CHAPTER")

    token = make_dev_jwt("ing_test_user_a")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        chapters_resp = client.get(
            f"{base_url}/api/v1/tutor/catalog",
            params={"class_num": class_num, "subject": subject_key},
            headers=headers,
        )
        if chapters_resp.status_code >= 500:
            pytest.skip(f"[infra-error] tutor catalog failed: {chapters_resp.status_code}")
        chapters_resp.raise_for_status()
        chapters = chapters_resp.json().get("chapters") or []
        if not chapters:
            pytest.skip("No NCERT chapters in catalog for NBM tutor tests")

        indexed = [c for c in chapters if c.get("indexed") and int(c.get("chunks_count") or 0) > 0]
        pool = indexed or chapters

        if chapter_override:
            chapter = next((c for c in pool if str(c.get("chapter_no")) == chapter_override), pool[0])
        else:
            chapter = pool[0]

        other = next(
            (c for c in pool if c.get("chapter_no") != chapter.get("chapter_no")),
            None,
        )

        concepts_resp = client.get(
            f"{base_url}/api/v1/tutor/catalog",
            params={
                "class_num": class_num,
                "subject": subject_key,
                "chapter_no": chapter["chapter_no"],
            },
            headers=headers,
        )
        concepts_resp.raise_for_status()
        concepts = concepts_resp.json().get("concepts") or []
        concept_entry = next((c for c in concepts if c.get("id") not in (None, "all")), None)

        return {
            "class_num": class_num,
            "subject_key": subject_key,
            "subject_slug": chapter.get("subject_slug") or subject_key,
            "chapter_no": int(chapter["chapter_no"]),
            "chapter_title": chapter.get("chapter_title") or chapter.get("title") or "",
            "filter_chapter_name": chapter.get("filter_chapter_name"),
            "ncert_document_id": chapter.get("ncert_document_id"),
            "concept": concept_entry.get("label") if concept_entry else None,
            "concept_id": concept_entry.get("id") if concept_entry else None,
            "other_chapter_no": int(other["chapter_no"]) if other else None,
            "other_chapter_title": (other.get("chapter_title") or other.get("title")) if other else None,
            "other_filter_chapter_name": other.get("filter_chapter_name") if other else None,
        }
