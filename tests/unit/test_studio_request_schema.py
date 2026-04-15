"""StudioRequest validation for context_mode."""

import pytest
from pydantic import ValidationError

from apps.api.schemas.studio import StudioRequest


def test_sources_only_requires_source():
    StudioRequest(
        task_type="quiz",
        source_ids=["a"],
        context_mode="sources_only",
    )
    with pytest.raises(ValidationError):
        StudioRequest(task_type="quiz", source_ids=[], context_mode="sources_only")


def test_chat_hybrid_requires_transcript_and_source():
    StudioRequest(
        task_type="quiz",
        source_ids=["x"],
        context_mode="chat_hybrid",
        chat_transcript="User: hi\nAssistant: hello",
    )
    with pytest.raises(ValidationError):
        StudioRequest(
            task_type="quiz",
            source_ids=["x"],
            context_mode="chat_hybrid",
            chat_transcript="",
        )
    with pytest.raises(ValidationError):
        StudioRequest(
            task_type="quiz",
            source_ids=[],
            context_mode="chat_hybrid",
            chat_transcript="some chat",
        )


def test_selection_only_requires_min_length_and_clears_sources():
    r = StudioRequest(
        task_type="mind_map",
        source_ids=["should-be-ignored"],
        context_mode="selection_only",
        selection_text="x" * 15,
    )
    assert r.source_ids == []
    assert r.selection_text == "x" * 15
    with pytest.raises(ValidationError):
        StudioRequest(
            task_type="mind_map",
            context_mode="selection_only",
            selection_text="short",
        )


def test_default_is_sources_only():
    r = StudioRequest(task_type="flashcards", source_ids=["s1"])
    assert r.context_mode == "sources_only"
