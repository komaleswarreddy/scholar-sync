"""GRD-04 Indian PII detection unit tests."""

from __future__ import annotations

import pytest

from packages.core.security.pii_detector import PIIDetector, PIIType


@pytest.fixture
def detector():
    return PIIDetector(redact_mode=True)


def test_detects_aadhaar(detector):
    text = "My Aadhaar is 2345 6789 0123 for verification."
    result = detector.detect(text)
    assert result["has_pii"] is True
    assert "aadhaar" in result["pii_types"]


def test_detects_indian_phone_plus91(detector):
    text = "Call me at +91-9876543210 anytime."
    result = detector.detect(text)
    assert result["has_pii"] is True
    assert "phone_in" in result["pii_types"]


def test_no_false_positive_gravity(detector):
    text = "Acceleration due to gravity is about 9.8 m/s² on Earth."
    result = detector.detect(text)
    assert result["has_pii"] is False


def test_no_false_positive_chapter_ref(detector):
    text = "See Chapter 12 on light reflection in the textbook."
    result = detector.detect(text)
    assert result["has_pii"] is False


def test_redact_aadhaar_masks_digits(detector):
    text = "Aadhaar 3456 7890 1234"
    redacted, info = detector.redact(text)
    assert "3456 7890 1234" not in redacted
    assert info["has_pii"] is True
