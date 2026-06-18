"""NBM-02: Pin grounding-related config defaults."""

from config.settings import settings


def test_nbm02_global_fallback_default_off():
    assert settings.CHAT_ALLOW_GLOBAL_KNOWLEDGE_FALLBACK is False


def test_nbm02_strict_grounding_default_on():
    assert settings.CHAT_STRICT_CONTEXT_GROUNDING is True
