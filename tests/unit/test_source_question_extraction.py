"""Unit tests for source question extraction normalization."""

from datetime import datetime, timedelta, timezone

from packages.core.services.source_question_extraction_service import (
    _filter_english_rows,
    _is_english_only_question,
    _is_stale_processing,
    _normalize_sections,
    _preview,
)


def test_normalize_sections_flattens_questions():
    payload = {
        "sections": [
            {
                "label": "Section A",
                "questions": [
                    {
                        "number": 1,
                        "preview": "A car accelerates",
                        "fullText": "A car accelerates from rest at 2 m/s² for 5 s. Find final velocity.",
                        "confidence": "high",
                    },
                    {
                        "number": 2,
                        "preview": "Ball thrown upward",
                        "fullText": "A ball is thrown upward with speed 20 m/s. Find max height.",
                    },
                ],
            }
        ]
    }
    rows = _normalize_sections(payload)
    assert len(rows) == 2
    assert rows[0]["question_number"] == 1
    assert rows[0]["section_label"] == "Section A"
    assert "accelerates" in rows[0]["full_text"]


def test_preview_truncates_long_text():
    long = "x" * 200
    preview = _preview(long)
    assert len(preview) <= 120
    assert preview.endswith("…")


def test_normalize_skips_invalid_questions():
    payload = {
        "sections": [
            {
                "label": None,
                "questions": [
                    {"number": "bad", "fullText": "too short"},
                    {"number": 3, "fullText": "Valid question with enough characters to pass."},
                ],
            }
        ]
    }
    rows = _normalize_sections(payload)
    assert len(rows) == 1
    assert rows[0]["question_number"] == 3


def test_stale_processing_without_timestamp():
    assert _is_stale_processing({"status": "processing"}) is True


def test_stale_processing_after_timeout():
    old = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    assert _is_stale_processing({"status": "processing", "started_at": old}) is True


def test_active_processing_not_stale():
    recent = datetime.now(timezone.utc).isoformat()
    assert _is_stale_processing({"status": "processing", "started_at": recent}) is False


def test_english_only_question_rejects_hindi_script():
    assert _is_english_only_question("Q1. धारा का मान ज्ञात कीजिए।") is False
    assert _is_english_only_question("Q2. Current through a resistor is 2A.") is True


def test_filter_english_rows_reindexes_after_drop():
    rows = [
        {
            "question_number": 1,
            "section_label": None,
            "preview": "Hindi",
            "full_text": "Q1. निम्नलिखित प्रश्न का उत्तर दीजिए।",
            "page_hint": None,
            "sort_order": 0,
            "confidence": "high",
        },
        {
            "question_number": 2,
            "section_label": None,
            "preview": "English",
            "full_text": "Q2. Explain ray diagram of convex lens image formation.",
            "page_hint": None,
            "sort_order": 1,
            "confidence": "high",
        },
    ]
    filtered = _filter_english_rows(rows)
    assert len(filtered) == 1
    assert filtered[0]["question_number"] == 1
    assert filtered[0]["sort_order"] == 0


def test_filter_english_rows_drops_instruction_block():
    rows = [
        {
            "question_number": 1,
            "section_label": None,
            "preview": "Instruction",
            "full_text": (
                "1. (vii) In Section E, Questions no. 36 to 38 are case study based questions "
                "carrying 4 marks each. SECTION A This section comprises Multiple Choice Questions."
            ),
            "page_hint": None,
            "sort_order": 0,
            "confidence": "high",
        },
        {
            "question_number": 2,
            "section_label": None,
            "preview": "Real question",
            "full_text": "2. Let f(x)=x^2. Find f'(2). (A) 2 (B) 4 (C) 6 (D) 8",
            "page_hint": None,
            "sort_order": 1,
            "confidence": "high",
        },
    ]
    filtered = _filter_english_rows(rows)
    assert len(filtered) == 1
    assert filtered[0]["question_number"] == 1
    assert "Find f'(2)" in filtered[0]["full_text"]
