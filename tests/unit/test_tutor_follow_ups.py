"""Unit tests for tutor follow-up suggestion fallbacks."""

from __future__ import annotations

from packages.core.services.tutor_notebook_bootstrap_service import fallback_follow_ups


def _civics_scope() -> dict:
    return {
        "class_num": 10,
        "subject_label": "Civics",
        "subject_key": "civics-polity",
        "chapter_no": 3,
        "chapter_title": "Gender, Religion and Caste",
        "concept": "",
    }


def test_fallback_overview_without_user_message():
    scope = _civics_scope()
    follow_ups = fallback_follow_ups(scope, "", "Chapter overview summary.")
    assert len(follow_ups) == 3
    assert all("Ch. 3" in item for item in follow_ups)


def test_fallback_after_exchange():
    scope = _civics_scope()
    follow_ups = fallback_follow_ups(
        scope,
        "How does caste affect political representation?",
        "Caste plays a significant role in influencing political representation in India.",
    )
    assert len(follow_ups) == 3
    assert any("example" in item.lower() for item in follow_ups)
    assert any("exam" in item.lower() for item in follow_ups)


def test_fallback_when_sources_missing():
    scope = _civics_scope()
    follow_ups = fallback_follow_ups(
        scope,
        "What is secularism?",
        "Not found in provided sources for this question.",
    )
    assert len(follow_ups) == 3
    assert any("rephrase" in item.lower() or "NCERT" in item for item in follow_ups)
