"""Source-scope meta queries (what are these documents about)."""

from packages.core.rag.metadata_query import is_source_scope_meta_query


def test_source_scope_meta_detects_two_sources_question():
    assert is_source_scope_meta_query("what are those two sources about")


def test_source_scope_meta_detects_documents_about():
    assert is_source_scope_meta_query("what are these documents about")


def test_source_scope_meta_rejects_specific_fact_question():
    assert not is_source_scope_meta_query("What is the distance formula in 3D?")
