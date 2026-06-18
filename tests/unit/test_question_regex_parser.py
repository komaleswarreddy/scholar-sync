"""Unit tests for regex question splitting."""

from packages.core.processing.question_regex_parser import regex_extract_questions


SAMPLE_WORKSHEET = """
Numericals for Motion

1. A car accelerates from rest at 2 m/s² for 5 s. Find final velocity.
2. A ball is thrown upward with speed 20 m/s. Find maximum height.
3. An object moves 10 m north then 6 m east. Find displacement.
"""


def test_regex_extract_numbered_questions():
    rows = regex_extract_questions(SAMPLE_WORKSHEET)
    assert len(rows) == 3
    assert rows[0]["question_number"] == 1
    assert "accelerates" in rows[0]["full_text"]
    assert rows[2]["question_number"] == 3


def test_regex_extract_q_prefix():
    text = "Q1. First problem here with enough text.\nQ2. Second problem here with enough text."
    rows = regex_extract_questions(text)
    assert len(rows) == 2
    assert rows[0]["question_number"] == 1


def test_regex_returns_empty_for_unstructured_text():
    text = "This is a paragraph without numbered questions at all."
    assert regex_extract_questions(text) == []


def test_regex_requires_minimum_questions():
    text = "1. Only one question in the document."
    assert regex_extract_questions(text) == []
