"""Unit tests for Studio output structure validators (STU-06..08 schema layer)."""

from packages.core.validation.studio_output_validators import (
    validate_flashcards_schema,
    validate_infographic_data,
    validate_mind_map_structure,
    validate_quiz_schema,
    validate_report,
    validate_slide_deck,
    validate_studio_output,
)


def test_validate_quiz_schema_good():
    data = {
        "title": "Photosynthesis Quiz",
        "questions": [
            {
                "question": "What is photosynthesis?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": "Because source.",
            }
        ],
    }
    result = validate_quiz_schema(data)
    assert result.valid


def test_validate_quiz_schema_bad_correct_answer():
    data = {
        "questions": [
            {
                "question": "Q?",
                "options": ["A", "B"],
                "correct_answer": "Z",
            }
        ]
    }
    result = validate_quiz_schema(data)
    assert not result.valid
    assert any("correct_answer" in e for e in result.errors)


def test_validate_flashcards_schema_good():
    cards = [{"front": "Term", "back": "Definition"}]
    assert validate_flashcards_schema(cards).valid


def test_validate_flashcards_schema_swapped_fields():
    cards = [{"front": "same", "back": "same"}]
    result = validate_flashcards_schema(cards)
    assert not result.valid


def test_validate_mind_map_structure_good():
    content = "# Topic\n## Subtopic A\n- Point 1\n- Point 2\n## Subtopic B\n- Point 3"
    assert validate_mind_map_structure(content).valid


def test_validate_mind_map_structure_duplicate_heading():
    content = "# Topic\n## Same\n- a\n## Same\n- b"
    result = validate_mind_map_structure(content)
    assert not result.valid


def test_validate_report_good():
    content = "# Study Guide\n\n## Section\nAccording to the source, photosynthesis converts light.\n"
    result = validate_report(content)
    assert result.valid


def test_validate_report_missing_heading():
    result = validate_report("plain text without headings")
    assert not result.valid


def test_validate_slide_deck_good():
    content = "## Slide 1: Intro\n- Bullet one\n\n---\n\n## Slide 2: Details\n- Bullet two"
    assert validate_slide_deck(content).valid


def test_validate_slide_deck_empty_slide():
    content = "## Title only\n\n---\n\n## Another\n"
    result = validate_slide_deck(content)
    assert not result.valid


def test_validate_infographic_data_good():
    data = {"title": "Infographic", "sections": [{"heading": "A", "body": "text"}]}
    assert validate_infographic_data(data).valid


def test_validate_studio_output_dispatch():
    payload = {"task_type": "quiz", "data": {"questions": []}}
    result = validate_studio_output(payload)
    assert not result.valid
