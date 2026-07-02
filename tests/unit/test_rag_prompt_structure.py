from pathlib import Path

from packages.core.prompts import load_prompt


def test_rag_prompt_contains_required_sections():
    p = Path(__file__).parent.parent.parent / "packages" / "core" / "prompts" / "templates" / "chat" / "rag_prompt.j2"
    txt = p.read_text(encoding="utf-8", errors="ignore")
    assert "RAG chat" in txt and "compact" in txt
    assert "## Grounding rules" in txt
    assert "## Context evidence from vector store" in txt
    assert "## What to answer" in txt
    assert "llm_task_query" in txt or "retrieval-aligned" in txt.lower()
    assert "## From your documents" in txt
    assert "Not found in provided sources" in txt


def test_rag_prompt_renders_with_context():
    out = load_prompt(
        "chat/rag_prompt.j2",
        context="[1] Bio: Plants use chlorophyll.",
        message="What is photosynthesis?",
        verbatim_user_message="What is photosynthesis?",
        primary_retrieval_query="photosynthesis",
        llm_task_query="photosynthesis",
        scope_focused_query="photosynthesis",
        context_chunk_count=1,
        chat_policy_block="",
        has_prior_conversation=False,
        has_chat_summary=False,
        classified_intent="explanation",
        tutor_strict_ncert_only=False,
        chat_global_fallback=False,
        document_summary=False,
        is_metadata_query=False,
    )
    assert "Context evidence" in out
    assert "Grounding rules" in out
    assert "photosynthesis" in out.lower()
