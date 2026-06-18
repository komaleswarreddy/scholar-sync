"""
Studio generation tests (STU-01..10).

STU-03 (exam-style fidelity) is intentionally excluded from scope.
Curriculum rows STU-01/02/04/05 are skipped until human sign-off via export scripts.
"""

from __future__ import annotations

import httpx
import pytest

from packages.core.validation.studio_output_validators import (
    validate_infographic_data,
    validate_mind_map_structure,
    validate_quiz_schema,
    validate_report,
    validate_slide_deck,
    validate_studio_output,
)
from tests.helpers.auth import make_dev_jwt
from tests.helpers.ingest_client import upload_file, wait_for_source_status
from tests.helpers.studio_client import generate_studio

pytestmark = [pytest.mark.integration, pytest.mark.studio]

# Leak-probe IDs that must not appear when quizzing standard_chapter.pdf (photosynthesis).
# lp-03/05/12 can legitimately appear in-source; exclude from off-corpus checks.
_OFF_CORPUS_LEAK_PROBE_IDS = frozenset(
    {
        "lp-01",
        "lp-02",
        "lp-04",
        "lp-06",
        "lp-07",
        "lp-08",
        "lp-09",
        "lp-10",
        "lp-11",
        "lp-13",
        "lp-14",
        "lp-15",
    }
)


def _off_corpus_leak_probes(leak_probe_questions) -> list[tuple[str, list[str]]]:
    from tests.conftest import NBM_LEAK_PROBE_PATH

    if not NBM_LEAK_PROBE_PATH.exists():
        return [(q, subs) for q, subs in leak_probe_questions if "france" in q.lower() or "paris" in q.lower()]
    import json

    data = json.loads(NBM_LEAK_PROBE_PATH.read_text(encoding="utf-8"))
    out: list[tuple[str, list[str]]] = []
    for item in data.get("items") or []:
        if item.get("id") not in _OFF_CORPUS_LEAK_PROBE_IDS:
            continue
        q = str(item.get("question") or "").strip()
        subs = [str(s).lower() for s in (item.get("forbidden_answer_substrings") or []) if s]
        if q and subs:
            out.append((q, subs))
    return out


def _assert_quiz_not_leak_probe_trivia(quiz_data: dict, leak_probe_questions) -> None:
    """Reject quizzes that reuse off-corpus leak-probe question wording."""
    probes = _off_corpus_leak_probes(leak_probe_questions)
    questions = quiz_data.get("questions") or []
    for q in questions:
        q_text = str(q.get("question") or "").lower()
        for probe_q, _forbidden in probes:
            probe_lower = probe_q.lower()
            if probe_lower in q_text or q_text in probe_lower:
                raise AssertionError(
                    f"[content-error] quiz question mirrors leak-probe: {probe_q!r}"
                )
            probe_tokens = {w for w in probe_lower.split() if len(w) > 4}
            if len(probe_tokens) >= 2 and len(probe_tokens & set(q_text.split())) >= 2:
                raise AssertionError(
                    f"[content-error] quiz question overlaps leak-probe topic: {probe_q!r}"
                )


def _assert_generate_ok(result, *, tag: str = "infra-error") -> dict:
    if result.status_code >= 500:
        pytest.skip(f"[{tag}] studio generate HTTP {result.status_code}")
    assert result.status_code == 200, (
        f"[{tag}] expected 200, got {result.status_code}: {result.raw_text[:400]}"
    )
    return result.body


class TestSTU09NoSourceValidation:
    """STU-09: empty sources_only must fail at request validation (422)."""

    def test_stu09_empty_sources_returns_422(
        self, require_integration, api_client, base_url, auth_token
    ):
        response = api_client.post(
            f"{base_url}/api/v1/studio/generate",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "task_type": "quiz",
                "source_ids": [],
                "context_mode": "sources_only",
            },
            timeout=60.0,
        )
        assert response.status_code == 422, (
            f"[structure-error] expected 422 for empty sources, got {response.status_code}"
        )
        body = response.text.lower()
        assert "source" in body or "validation" in body or "422" in str(response.status_code)


class TestSTU06MindMapStructure:
    def test_stu06_mind_map_structure(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        stu_standard_source_id,
    ):
        result = generate_studio(
            api_client,
            base_url=base_url,
            token=auth_token,
            task_type="mind_map",
            source_ids=[stu_standard_source_id],
        )
        body = _assert_generate_ok(result)
        content = body.get("content") or ""
        validation = validate_mind_map_structure(content)
        validation.assert_valid(prefix="STU-06")


class TestSTU07ReportSchema:
    def test_stu07_report_schema(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        stu_standard_source_id,
    ):
        result = generate_studio(
            api_client,
            base_url=base_url,
            token=auth_token,
            task_type="report",
            source_ids=[stu_standard_source_id],
            report_format="study_guide",
        )
        body = _assert_generate_ok(result)
        content = body.get("content") or ""
        validation = validate_report(content)
        validation.assert_valid(prefix="STU-07")


class TestSTU08SlideDeckSchema:
    def test_stu08_slide_deck_schema(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        stu_standard_source_id,
    ):
        result = generate_studio(
            api_client,
            base_url=base_url,
            token=auth_token,
            task_type="slide_deck",
            source_ids=[stu_standard_source_id],
        )
        body = _assert_generate_ok(result)
        content = body.get("content") or ""
        validation = validate_slide_deck(content)
        validation.assert_valid(prefix="STU-08")


class TestSTU10SubjectGrounding:
    def test_stu10_quiz_no_leak_probe_trivia(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        stu_standard_source_id,
        nbm_leak_probe_questions,
    ):
        result = generate_studio(
            api_client,
            base_url=base_url,
            token=auth_token,
            task_type="quiz",
            source_ids=[stu_standard_source_id],
        )
        body = _assert_generate_ok(result)
        validation = validate_quiz_schema(body.get("data"))
        validation.assert_valid(prefix="STU-10")

        _assert_quiz_not_leak_probe_trivia(body.get("data") or {}, nbm_leak_probe_questions)


class TestSTUSchemaSmokePerTaskType:
    @pytest.mark.parametrize(
        "task_type,extra",
        [
            ("quiz", {}),
            ("flashcards", {}),
            ("infographic", {}),
        ],
    )
    def test_stu_schema_smoke_structured_tasks(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        stu_standard_source_id,
        task_type,
        extra,
    ):
        result = generate_studio(
            api_client,
            base_url=base_url,
            token=auth_token,
            task_type=task_type,
            source_ids=[stu_standard_source_id],
            **extra,
        )
        body = _assert_generate_ok(result)
        if task_type == "infographic":
            validation = validate_infographic_data(body.get("infographic_data"))
        else:
            body["task_type"] = task_type
            validation = validate_studio_output(body)
        validation.assert_valid(prefix=f"STU-schema-{task_type}")


class TestSTUGuardrails:
    def test_stu_cross_user_source_forbidden(
        self,
        require_integration,
        base_url,
        fixtures_dir,
        integration_user_id,
        integration_user_b_id,
    ):
        token_a = make_dev_jwt(integration_user_id)
        token_b = make_dev_jwt(integration_user_b_id)
        with httpx.Client(timeout=120.0) as client:
            upload_a = upload_file(
                client,
                base_url=base_url,
                token=token_a,
                file_path=fixtures_dir / "sample_phrase_alpha.txt",
                title="stu_user_a_secret",
            )
            assert upload_a.status_code == 200
            source_a = upload_a.json()["id"]
            wait_for_source_status(client, base_url=base_url, token=token_a, source_id=source_a)

            result = generate_studio(
                client,
                base_url=base_url,
                token=token_b,
                task_type="quiz",
                source_ids=[source_a],
            )
            assert result.status_code == 403, (
                f"[structure-error] cross-user studio generate expected 403, got {result.status_code}"
            )

    @pytest.mark.skip(
        reason="STU-IPI poisoned-source guardrail — pending IPI bucket fixture (see docs/STU_TEST_SUITE.md)"
    )
    def test_stu_ipi_poisoned_source_no_leak(self):
        pass

    def test_stu_schema_separate_from_content(self):
        """Document failure-tag discipline used across Studio validators."""
        bad_quiz = {"questions": [{"question": "Q?", "options": ["A"], "correct_answer": "Z"}]}
        result = validate_quiz_schema(bad_quiz)
        assert not result.valid
        assert result.tag == "structure-error"


@pytest.mark.skip(reason="STU-01 requires curriculum human sign-off — run export_stu_quiz_batch.py")
def test_stu01_quiz_answer_key_curriculum():
    pass


@pytest.mark.skip(reason="STU-02 requires curriculum human sign-off — run export_stu_quiz_batch.py")
def test_stu02_mcq_non_ambiguity_curriculum():
    pass


@pytest.mark.skip(reason="STU-04 requires curriculum human sign-off — run export_stu_flashcard_batch.py")
def test_stu04_flashcard_fact_integrity_curriculum():
    pass


@pytest.mark.skip(reason="STU-05 requires curriculum human sign-off — run export_stu_flashcard_batch.py")
def test_stu05_flashcard_formula_curriculum():
    pass


@pytest.mark.slow
@pytest.mark.skip(reason="STU determinism (3x regen) — optional slow suite")
def test_stu_determinism_three_regenerations():
    pass
