"""Intent gate must not block common academic phrasing (RET-04 regression)."""

from packages.core.security.intent_gate import IntentGate


def test_role_play_in_photynthesis_not_entertainment_block():
    gate = IntentGate()
    result = gate.check_and_block("What role does carbon dioxide play in photosynthesis?")
    assert result["allowed"] is True
    assert result["blocked"] is False
