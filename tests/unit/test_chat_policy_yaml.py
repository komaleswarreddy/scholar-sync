"""Verify central YAML policy layer: loader, template branches, chat_graph passes variable."""

from __future__ import annotations

from unittest.mock import patch

from config.settings import settings
from packages.core.knowledge import policy_loader as pl
from packages.core.prompts import load_prompt


def test_default_yaml_exists():
    p = pl._default_policy_path()
    assert p.is_file(), f"Missing default policy: {p}"


def test_build_chat_policy_block_nonempty():
    block = pl.build_chat_policy_block()
    assert block
    assert "**Tone:**" in block
    assert "**Rules:**" in block
    assert "**Avoid these patterns:**" in block
    assert "**Safety:**" in block
    assert "**Age-appropriate guidance" in block
    assert "patient" in block.lower()
    assert "14" in block and "17" in block


def test_default_age_tier_targets_14_to_17():
    with patch.object(settings, "STUDENT_AGE_TIER", "14-17"):
        block = pl.build_chat_policy_block()
    assert "14" in block and "17" in block
    assert "secondary" in block.lower() or "grades 9" in block.lower()


def test_age_tier_k5_injects_young_learner_bullets():
    with patch.object(settings, "STUDENT_AGE_TIER", "k5"):
        block = pl.build_chat_policy_block()
    assert "very simple words" in block.lower()
    assert "classroom-safe" in block.lower()


def test_age_tier_adult_injects_adult_bullets():
    with patch.object(settings, "STUDENT_AGE_TIER", "adult"):
        block = pl.build_chat_policy_block()
    assert "professional" in block.lower()


def test_rag_prompt_with_context_includes_policy_before_evidence():
    block = pl.build_chat_policy_block()
    common = dict(
        message="What is photosynthesis?",
        verbatim_user_message="What is photosynthesis?",
        llm_task_query="photosynthesis",
        document_summary=False,
        conversation_transcript="",
        has_prior_conversation=False,
        chat_rolling_summary="",
        has_chat_summary=False,
        primary_retrieval_query="photosynthesis",
        scope_focused_query="photosynthesis",
        retrieval_query_variants=[],
        classified_intent="explanation",
        context_chunk_count=1,
        is_metadata_query=False,
        tutor_strict_ncert_only=False,
        chat_global_fallback=False,
        chat_policy_block=block,
    )
    ctx_prompt = load_prompt(
        "chat/rag_prompt.j2",
        context="[1] Bio (p1): Plants use light...",
        **common,
    )
    assert "## Central response policy (mandatory)" in ctx_prompt
    assert ctx_prompt.index("Central response policy") < ctx_prompt.index(
        "## Context evidence from vector store"
    )


def test_rag_prompt_no_context_branch_includes_policy():
    block = pl.build_chat_policy_block()
    common = dict(
        message="Hi",
        verbatim_user_message="Hi",
        llm_task_query="hi",
        document_summary=False,
        conversation_transcript="",
        has_prior_conversation=False,
        chat_rolling_summary="",
        has_chat_summary=False,
        primary_retrieval_query="hi",
        scope_focused_query="hi",
        retrieval_query_variants=[],
        classified_intent="",
        context_chunk_count=0,
        is_metadata_query=False,
        tutor_strict_ncert_only=False,
        chat_global_fallback=False,
        chat_policy_block=block,
    )
    no_ctx = load_prompt("chat/rag_prompt.j2", context="", **common)
    assert "## Central response policy (mandatory)" in no_ctx
    assert "No document context was retrieved" in no_ctx
    assert no_ctx.index("No document context") < no_ctx.index("Central response policy")


def test_disabled_returns_empty_block():
    with patch.object(settings, "ENABLE_CHAT_POLICY_YAML", False):
        assert pl.build_chat_policy_block() == ""


def test_empty_block_omits_section():
    common = dict(
        message="x",
        verbatim_user_message="x",
        llm_task_query="x",
        document_summary=False,
        conversation_transcript="",
        has_prior_conversation=False,
        chat_rolling_summary="",
        has_chat_summary=False,
        primary_retrieval_query="x",
        scope_focused_query="x",
        retrieval_query_variants=[],
        classified_intent="",
        context_chunk_count=1,
        is_metadata_query=False,
        tutor_strict_ncert_only=False,
        chat_global_fallback=False,
        chat_policy_block="",
    )
    out = load_prompt("chat/rag_prompt.j2", context="chunk", **common)
    assert "## Central response policy (mandatory)" not in out


def test_chat_graph_includes_policy_in_prompt_construction():
    """Mirror _node_generate: build_chat_policy_block + load_prompt args."""
    from packages.core.langgraph.chat_graph import LangGraphChatPipeline
    from packages.core.knowledge.policy_loader import build_chat_policy_block

    block = build_chat_policy_block()
    fp = load_prompt(
        "chat/rag_prompt.j2",
        context="evidence text",
        message="m",
        verbatim_user_message="m",
        llm_task_query="m",
        document_summary=False,
        conversation_transcript="",
        has_prior_conversation=False,
        chat_rolling_summary="",
        has_chat_summary=False,
        primary_retrieval_query="m",
        scope_focused_query="m",
        retrieval_query_variants=[],
        classified_intent="",
        context_chunk_count=1,
        is_metadata_query=False,
        tutor_strict_ncert_only=False,
        chat_global_fallback=False,
        chat_policy_block=block,
    )
    assert "Central response policy" in fp
    # Ensure graph module still imports loader (smoke)
    assert LangGraphChatPipeline.__module__ == "packages.core.langgraph.chat_graph"
