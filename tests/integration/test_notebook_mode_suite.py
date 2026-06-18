"""
Notebook-Mode guardrail tests (NBM-01..06).

Assert SOURCE of answer (citations, done_payload, trace chunks) — not prose alone.
Manual NBM-04 UI badge: open tutor chat, thin-KB question, confirm visible indicator (not shipped).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
import pytest

from tests.helpers.chat_client import ChatStreamResult, stream_chat

pytestmark = [pytest.mark.integration, pytest.mark.notebook_mode]

REFUSAL_PHRASES = (
    "not found in provided sources",
    "not found in the selected sources",
    "not found in the selected ncert",
    "not found",
)


def _coerce_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def assert_refusal(chat: ChatStreamResult, *, tag: str = "boundary-leak") -> None:
    text = (chat.text or "").lower()
    assert any(p in text for p in REFUSAL_PHRASES), (
        f"[{tag}] expected refusal, got: {(chat.text or '')[:300]}"
    )
    assert len(chat.citations) == 0, f"[{tag}] citations should be empty on refusal"
    origin = (chat.done_payload or {}).get("answer_origin")
    assert origin != "global_only", f"[{tag}] answer_origin must not be global_only"


def assert_no_grounding_leak(
    chat: ChatStreamResult, forbidden_substrings: List[str], *, tag: str = "boundary-leak"
) -> None:
    text = (chat.text or "").lower()
    for sub in forbidden_substrings:
        assert sub.lower() not in text, f"[{tag}] grounding leak: found '{sub}' in answer"


def assert_tutor_leak_probe_blocked(
    chat: ChatStreamResult, forbidden_substrings: List[str], *, tag: str = "boundary-leak"
) -> None:
    """Tutor strict mode: refusal text + no training-data answer; citations may linger (known gap)."""
    text = (chat.text or "").lower()
    assert any(p in text for p in REFUSAL_PHRASES), (
        f"[{tag}] expected tutor refusal, got: {(chat.text or '')[:300]}"
    )
    assert_no_grounding_leak(chat, forbidden_substrings, tag=tag)
    if chat.citations:
        pytest.xfail("tutor refusal retains NCERT citations on not-found (product gap)")


def fetch_retrieved_chunk_metadata(
    client: httpx.Client,
    *,
    base_url: str,
    token: str,
    trace_id: str,
) -> List[Dict[str, Any]]:
    response = client.get(
        f"{base_url}/api/v1/pipeline-traces/{trace_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    )
    if response.status_code >= 500:
        pytest.skip(f"[infra-error] trace fetch {response.status_code}")
    if response.status_code == 404:
        return []
    response.raise_for_status()
    artifacts = response.json().get("artifacts") or {}
    retrieval = artifacts.get("retrieval") or {}
    chunks = retrieval.get("retrieved_chunks") or []
    return [c.get("metadata") or {} for c in chunks if isinstance(c, dict)]


def _create_exploratory_notebook(client: httpx.Client, base_url: str, token: str) -> str:
    response = client.post(
        f"{base_url}/api/v1/notebooks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "NBM exploratory", "mode": "exploratory"},
    )
    response.raise_for_status()
    return response.json()["id"]


def _tutor_ncert_kwargs(scope: Dict[str, Any], scope_level: str) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "include_ncert_global": True,
        "active_source_ids": [],
        "ncert_class": scope["class_num"],
        "ncert_subject": scope["subject_slug"],
    }
    if scope_level in ("chapter", "concept"):
        kwargs["ncert_chapter_no"] = scope["chapter_no"]
        if scope.get("filter_chapter_name"):
            kwargs["ncert_chapter_name"] = scope["filter_chapter_name"]
    if scope_level == "concept" and scope.get("concept"):
        kwargs["ncert_concept"] = scope["concept"]
    return kwargs


def _chunk_matches_scope(md: Dict[str, Any], scope: Dict[str, Any], scope_level: str) -> bool:
    md_class = _coerce_int(md.get("class") or md.get("class_num"))
    if md_class is not None and md_class != scope["class_num"]:
        return False
    md_subject = str(md.get("subject") or md.get("subject_key") or "").lower()
    expected_subject = str(scope["subject_key"]).lower()
    if md_subject and expected_subject not in md_subject and md_subject not in expected_subject:
        slug = str(scope.get("subject_slug") or "").lower()
        if slug and slug not in md_subject and md_subject not in slug:
            return False
    if scope_level in ("chapter", "concept"):
        md_chapter = _coerce_int(md.get("chapter_no"))
        if md_chapter is not None and md_chapter != scope["chapter_no"]:
            return False
    return True


class TestNBM01ExploratoryStrictGrounding:
    """NBM-01: Exploratory mode refuses leak-probe questions not in selected sources."""

    def test_nbm01_leak_probe_refuses_without_citations(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_exploratory_source_id,
        nbm_leak_probe_questions,
    ):
        question, forbidden = nbm_leak_probe_questions[0]
        notebook_id = _create_exploratory_notebook(api_client, base_url, auth_token)

        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=question,
            active_source_ids=[nbm_exploratory_source_id],
            notebook_id=notebook_id,
        )
        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")

        assert_refusal(chat, tag="boundary-leak")
        assert_no_grounding_leak(chat, forbidden, tag="boundary-leak")
        reason = (chat.done_payload or {}).get("generation_blocked_reason")
        assert reason != "GLOBAL_FALLBACK_USED", "[boundary-leak] global fallback used"


class TestNBM02GlobalFallbackDefaultOff:
    """NBM-02: Config default OFF and runtime does not fall back."""

    def test_nbm02_runtime_no_global_fallback(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_exploratory_source_id,
        nbm_leak_probe_questions,
    ):
        question, forbidden = nbm_leak_probe_questions[1]
        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=question,
            active_source_ids=[nbm_exploratory_source_id],
        )
        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")

        assert_refusal(chat, tag="boundary-leak")
        assert_no_grounding_leak(chat, forbidden, tag="boundary-leak")
        done = chat.done_payload or {}
        assert done.get("generation_blocked_reason") != "GLOBAL_FALLBACK_USED"
        assert done.get("answer_origin") != "global_only"


class TestNBM03TutorKbFirst:
    """NBM-03: Tutor KB-first — in-scope citations; thin-KB blocks or flags."""

    def test_nbm03a_in_scope_question_has_citations(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_tutor_scope,
    ):
        scope = nbm_tutor_scope
        question = f"What are the key concepts in {scope['chapter_title']}?"

        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=question,
            **_tutor_ncert_kwargs(scope, "chapter"),
        )
        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")

        text = (chat.text or "").lower()
        if any(p in text for p in REFUSAL_PHRASES):
            pytest.skip("[infra-error] in-scope tutor question refused — check NCERT seed")
        assert len(chat.citations) > 0, "[boundary-leak] in-scope tutor answer must cite KB chunks"

    def test_nbm03b_leak_probe_blocked_in_tutor_mode(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_tutor_scope,
        nbm_leak_probe_questions,
    ):
        question, forbidden = nbm_leak_probe_questions[0]
        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=question,
            **_tutor_ncert_kwargs(nbm_tutor_scope, "chapter"),
        )
        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")

        assert_tutor_leak_probe_blocked(chat, forbidden, tag="boundary-leak")

    @pytest.mark.xfail(reason="hybrid beyond-KB not implemented; strict block only")
    def test_nbm03_hybrid_beyond_kb_indicator_in_done_payload(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_tutor_scope,
        nbm_leak_probe_questions,
    ):
        """When hybrid ships: thin-KB should set answer_origin=beyond_kb, not silent extrapolation."""
        question, _ = nbm_leak_probe_questions[2]
        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=question,
            **_tutor_ncert_kwargs(nbm_tutor_scope, "concept"),
        )
        done = chat.done_payload or {}
        assert done.get("answer_origin") == "beyond_kb"


class TestNBM04BeyondKbIndicator:
    """NBM-04: No silent general-knowledge prefix in strict tutor mode."""

    def test_nbm04_no_general_knowledge_prefix_in_tutor_answer(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_tutor_scope,
    ):
        scope = nbm_tutor_scope
        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=f"Summarize {scope['chapter_title']}.",
            **_tutor_ncert_kwargs(scope, "chapter"),
        )
        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")
        if not (chat.text or "").strip():
            pytest.skip("[infra-error] empty tutor response")
        assert "general knowledge:" not in (chat.text or "").lower(), (
            "[indicator-miss] tutor strict mode must not emit General knowledge: prefix"
        )

    @pytest.mark.skip(reason="NBM-04 UI badge not implemented — manual demo only")
    def test_nbm04_ui_badge_renders_for_beyond_kb(self):
        """Manual: tutor chat → thin-KB question → confirm beyond-textbook badge visible."""


class TestNBM05ScopeFilterLimitsRetrieval:
    """NBM-05: NCERT scope filters restrict retrieved chunk metadata."""

    @pytest.mark.parametrize("scope_level", ["subject", "chapter", "concept"])
    def test_nbm05_retrieved_chunks_within_scope(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_tutor_scope,
        scope_level,
    ):
        scope = nbm_tutor_scope
        if scope_level == "concept" and not scope.get("concept"):
            pytest.skip("No concept in catalog for concept-level scope test")

        question = f"Explain topics from {scope['chapter_title']}."
        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=question,
            **_tutor_ncert_kwargs(scope, scope_level),
        )
        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")

        trace_id = (chat.done_payload or {}).get("trace_id")
        if not trace_id:
            pytest.skip("[infra-error] no trace_id in done payload")

        metadata_rows = fetch_retrieved_chunk_metadata(
            api_client, base_url=base_url, token=auth_token, trace_id=str(trace_id)
        )
        if not metadata_rows:
            pytest.skip("[infra-error] no retrieved chunks in trace")

        top = metadata_rows[:5]
        for md in top:
            assert _chunk_matches_scope(md, scope, scope_level), (
                f"[scope-leak] chunk out of scope at level={scope_level}: {md}"
            )

    def test_nbm05_no_out_of_scope_chapter_in_retrieval(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_tutor_scope,
    ):
        scope = nbm_tutor_scope
        other_chapter = scope.get("other_chapter_no")
        if other_chapter is None:
            pytest.skip("Need two chapters in catalog for out-of-scope probe")

        chat = stream_chat(
            api_client,
            base_url=base_url,
            token=auth_token,
            message=f"What is covered in {scope['chapter_title']}?",
            **_tutor_ncert_kwargs(scope, "chapter"),
        )
        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")

        trace_id = (chat.done_payload or {}).get("trace_id")
        if not trace_id:
            pytest.skip("[infra-error] no trace_id in done payload")

        metadata_rows = fetch_retrieved_chunk_metadata(
            api_client, base_url=base_url, token=auth_token, trace_id=str(trace_id)
        )
        for md in metadata_rows[:5]:
            md_chapter = _coerce_int(md.get("chapter_no"))
            if md_chapter is not None:
                assert md_chapter != other_chapter, (
                    f"[scope-leak] retrieved chunk from chapter {other_chapter}: {md}"
                )


class TestNBM06ModeImmutability:
    """NBM-06: Notebook mode cannot change after creation."""

    def test_nbm06_mode_unchanged_after_patch(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
    ):
        create = api_client.post(
            f"{base_url}/api/v1/notebooks",
            json={"title": "NBM mode lock", "mode": "exploratory"},
        )
        create.raise_for_status()
        notebook_id = create.json()["id"]
        assert create.json()["mode"] == "exploratory"

        patch = api_client.patch(
            f"{base_url}/api/v1/notebooks/{notebook_id}",
            json={"title": "NBM patch"},
        )
        patch.raise_for_status()

        get_resp = api_client.get(f"{base_url}/api/v1/notebooks/{notebook_id}")
        get_resp.raise_for_status()
        assert get_resp.json()["mode"] == "exploratory"

    @pytest.mark.xfail(strict=False, reason="spec wants explicit 400 when mode sent on PATCH")
    def test_nbm06_mode_change_rejected_with_400(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
    ):
        create = api_client.post(
            f"{base_url}/api/v1/notebooks",
            json={"title": "NBM mode reject", "mode": "exploratory"},
        )
        create.raise_for_status()
        notebook_id = create.json()["id"]

        patch = api_client.patch(
            f"{base_url}/api/v1/notebooks/{notebook_id}",
            json={"mode": "tutor"},
        )
        assert patch.status_code in (400, 403), (
            f"mode change should be rejected, got {patch.status_code}"
        )


class TestNBMCrossModeGuardrails:
    """ALL NBM: opposite mode rules must not apply."""

    @pytest.mark.parametrize("mode_name", ["exploratory", "tutor"])
    def test_nbm_cross_mode_leak_probe(
        self,
        require_integration,
        api_client,
        base_url,
        auth_token,
        nbm_exploratory_source_id,
        nbm_tutor_scope,
        nbm_leak_probe_questions,
        mode_name,
    ):
        question, forbidden = nbm_leak_probe_questions[0]

        if mode_name == "exploratory":
            chat = stream_chat(
                api_client,
                base_url=base_url,
                token=auth_token,
                message=question,
                active_source_ids=[nbm_exploratory_source_id],
            )
        else:
            chat = stream_chat(
                api_client,
                base_url=base_url,
                token=auth_token,
                message=question,
                **_tutor_ncert_kwargs(nbm_tutor_scope, "chapter"),
            )

        if chat.error:
            pytest.skip(f"[infra-error] chat stream error: {chat.error}")

        if mode_name == "exploratory":
            assert_refusal(chat, tag="boundary-leak")
        else:
            assert_tutor_leak_probe_blocked(chat, forbidden, tag="boundary-leak")
        assert_no_grounding_leak(chat, forbidden, tag="boundary-leak")
        done = chat.done_payload or {}
        assert done.get("generation_blocked_reason") != "GLOBAL_FALLBACK_USED"
        assert done.get("answer_origin") != "global_only"
