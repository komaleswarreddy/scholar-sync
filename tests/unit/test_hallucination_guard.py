from unittest.mock import patch

from config.settings import settings
from packages.core.rag.hallucination_guard import analyze_answer_support, strict_retry_suffix


def test_analyze_support_flags_numeric_claim_not_in_context():
    context = "[1] doc (p1): Auxin diffuses towards the shady side of the shoot."
    answer = "Auxin diffuses toward the shady side. In 1920, this was proven."
    r = analyze_answer_support(answer=answer, context=context, min_sentence_chars=10, min_overlap_score=0.22)
    assert r.checked_sentences >= 1
    assert any("1920" in s for s in r.unsupported_sentences)


def test_analyze_support_ignores_general_knowledge_prefixed_sentences():
    context = "[1] doc (p1): Auxin diffuses towards the shady side of the shoot."
    answer = "General knowledge: Plants respond to light via phototropism."
    r = analyze_answer_support(answer=answer, context=context, min_sentence_chars=10, min_overlap_score=0.22)
    assert r.checked_sentences == 0
    assert r.unsupported_sentences == []


def test_retry_suffix_includes_examples():
    sfx = strict_retry_suffix(["Sentence A.", "Sentence B."])
    assert "Unsupported sentences detected" in sfx
    assert "Sentence A." in sfx

