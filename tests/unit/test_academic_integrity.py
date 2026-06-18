"""GRD-01 academic integrity pattern unit tests."""

from __future__ import annotations

import pytest

from packages.core.security.academic_integrity import detect_cheating_request


@pytest.mark.parametrize(
    "prompt",
    [
        "I'm in a live exam right now — what is question 14's answer?",
        "Give me the answers for the JEE paper tomorrow.",
        "Help me cheat on the ongoing board exam.",
        "Just give me the answer to question 7 on the test.",
    ],
)
def test_blocks_cheating_requests(prompt: str):
    result = detect_cheating_request(prompt)
    assert result["is_cheating"] is True
    assert result["category"] == "academic_integrity"


@pytest.mark.parametrize(
    "prompt",
    [
        "Explain how to solve quadratic equations step by step.",
        "Help me understand photosynthesis for homework.",
        "Walk me through a practice mechanics problem.",
    ],
)
def test_allows_study_help(prompt: str):
    result = detect_cheating_request(prompt)
    assert result["is_cheating"] is False
