"""Unit tests for subject-aware tutor studio recommendations."""

from __future__ import annotations

from packages.core.services.tutor_notebook_bootstrap_service import (
    studio_recommendations_for_scope,
)


def test_civics_fallback_prefers_slide_deck_and_quiz():
    scope = {
        "subject_key": "civics-polity",
        "subject_slug": "social_science",
        "chapter_no": 3,
        "chapter_title": "Gender, Religion and Caste",
    }
    recs = studio_recommendations_for_scope(scope)
    auto_types = [r["type"] for r in recs if r["auto_generate"]]
    assert auto_types == ["slide_deck", "quiz"]


def test_science_fallback_prefers_flashcards_and_quiz():
    scope = {
        "subject_key": "science",
        "subject_slug": "science",
        "chapter_no": 6,
        "chapter_title": "Life Processes",
    }
    recs = studio_recommendations_for_scope(scope)
    auto_types = [r["type"] for r in recs if r["auto_generate"]]
    assert auto_types == ["flashcards", "quiz"]
