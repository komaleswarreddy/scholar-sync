"""OpenAI Moderation API wiring: model name, response shape, optional live omni check."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from config.settings import settings
from packages.core.security.openai_moderation import (
    check_moderation,
    is_openai_moderation_configured,
)


def test_check_moderation_empty_input_no_api_call():
    with patch("packages.core.security.openai_moderation._get_openai_client") as mock_gc:
        r = check_moderation("   ")
        mock_gc.assert_not_called()
    assert r == {"flagged": False, "categories": {}, "category_scores": {}}


def test_check_moderation_uses_settings_model():
    """Ensures omni (or any configured) moderation model is passed to the API."""
    fake_first = MagicMock()
    fake_first.flagged = False
    fake_first.categories = {}
    fake_first.category_scores = {}
    fake_resp = MagicMock()
    fake_resp.results = [fake_first]

    with patch("packages.core.security.openai_moderation._get_openai_client") as mock_gc:
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = fake_resp
        mock_gc.return_value = mock_client
        with patch.object(settings, "OPENAI_API_KEY", "sk-test-key"):
            with patch.object(settings, "OPENAI_MODERATION_MODEL", "omni-moderation-latest"):
                r = check_moderation("What is photosynthesis?")

    mock_client.moderations.create.assert_called_once()
    kwargs = mock_client.moderations.create.call_args.kwargs
    assert kwargs.get("model") == "omni-moderation-latest"
    assert kwargs.get("input") == "What is photosynthesis?"
    assert r["flagged"] is False


def test_check_moderation_model_override_kwarg():
    fake_first = MagicMock(flagged=False, categories={}, category_scores={})
    fake_resp = MagicMock(results=[fake_first])
    with patch("packages.core.security.openai_moderation._get_openai_client") as mock_gc:
        mock_client = MagicMock()
        mock_client.moderations.create.return_value = fake_resp
        mock_gc.return_value = mock_client
        with patch.object(settings, "OPENAI_API_KEY", "sk-test"):
            check_moderation("x", model="text-moderation-stable")
    kwargs = mock_client.moderations.create.call_args.kwargs
    assert kwargs.get("model") == "text-moderation-stable"


def test_live_omni_moderation_roundtrip():
    """
    Optional: verifies the real API with OPENAI_API_KEY and omni-moderation-latest.
    Run: OPENAI_RUN_MODERATION_LIVE=1 pytest tests/unit/test_openai_moderation_check.py -k live -v
    """
    if os.environ.get("OPENAI_RUN_MODERATION_LIVE") != "1":
        pytest.skip("Set OPENAI_RUN_MODERATION_LIVE=1 to exercise the live Moderation API")
    if not is_openai_moderation_configured():
        pytest.skip("OPENAI_API_KEY not configured")
    benign = "Explain the water cycle for a science class."
    r = check_moderation(benign, model=getattr(settings, "OPENAI_MODERATION_MODEL", "omni-moderation-latest"))
    assert "flagged" in r
    assert isinstance(r.get("flagged"), bool)
    assert r.get("flagged") is False, f"Unexpected flag on benign text: {r}"
    cats = r.get("categories") or {}
    scores = r.get("category_scores") or {}
    assert isinstance(cats, dict) and isinstance(scores, dict)
