"""Output moderation lenience: educational answers vs hard categories."""

from unittest.mock import patch

import pytest

from config.settings import settings
from packages.core.security.openai_moderation import (
    educational_rag_output_heuristic,
    moderation_indicates_block_output,
)


REFLEX_ANSWER = (
    "A reflex action occurs before the brain processes pain because it is mediated by a **reflex arc** "
    "that operates within the spinal cord. This mechanism allows for rapid responses to stimuli without "
    "the need for the brain's involvement, enabling a quicker reaction to potentially harmful situations."
)


def test_heuristic_matches_typical_biology_answer():
    assert educational_rag_output_heuristic(REFLEX_ANSWER) is True


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ok", False),
        ("x" * 40, False),
        ("The **mitosis** phase separates sister chromatids in the nucleus because the spindle apparatus.", True),
    ],
)
def test_heuristic_length_and_stem(text, expected):
    assert educational_rag_output_heuristic(text) is expected


def test_lenient_allows_flagged_soft_categories_when_heuristic_passes():
    result = {
        "flagged": True,
        "categories": {"violence": True, "self-harm": True},
        "category_scores": {"violence": 0.42, "self-harm": 0.38},
    }
    with patch.object(settings, "MODERATION_OUTPUT_LENIENT", True):
        with patch.object(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False):
            assert moderation_indicates_block_output(result, REFLEX_ANSWER) is False


def test_lenient_blocks_high_soft_scores():
    result = {
        "flagged": True,
        "categories": {"violence": True},
        "category_scores": {"violence": 0.95},
    }
    with patch.object(settings, "MODERATION_OUTPUT_LENIENT", True):
        with patch.object(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False):
            assert moderation_indicates_block_output(result, REFLEX_ANSWER) is True


def test_lenient_blocks_sexual_category():
    result = {
        "flagged": True,
        "categories": {"sexual": True},
        "category_scores": {"sexual": 0.9},
    }
    with patch.object(settings, "MODERATION_OUTPUT_LENIENT", True):
        with patch.object(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False):
            assert moderation_indicates_block_output(result, REFLEX_ANSWER) is True


def test_lenient_blocks_harassment_category():
    result = {
        "flagged": True,
        "categories": {"harassment": True},
        "category_scores": {"harassment": 0.6},
    }
    with patch.object(settings, "MODERATION_OUTPUT_LENIENT", True):
        with patch.object(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False):
            assert moderation_indicates_block_output(result, REFLEX_ANSWER) is True


def test_lenient_off_matches_strict_flagged():
    result = {"flagged": True, "categories": {}, "category_scores": {"violence": 0.1}}
    with patch.object(settings, "MODERATION_OUTPUT_LENIENT", False):
        with patch.object(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False):
            assert moderation_indicates_block_output(result, REFLEX_ANSWER) is True


def test_instructions_score_blocks_bypass():
    result = {
        "flagged": True,
        "categories": {"self-harm": True},
        "category_scores": {"self-harm": 0.2, "self-harm/instructions": 0.9},
    }
    with patch.object(settings, "MODERATION_OUTPUT_LENIENT", True):
        with patch.object(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False):
            assert moderation_indicates_block_output(result, REFLEX_ANSWER) is True
