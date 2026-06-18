"""Unit tests for FileValidator (ING-06)."""

from packages.core.security.file_validator import FileValidator


def test_rejects_exe():
    validator = FileValidator()
    ok, msg = validator.validate("malware.exe", "application/octet-stream", b"MZ")
    assert not ok
    assert "not supported" in msg.lower()


def test_accepts_valid_pdf_header():
    validator = FileValidator()
    ok, msg = validator.validate("doc.pdf", "application/pdf", b"%PDF-1.4 test")
    assert ok
    assert msg == ""


def test_rejects_fake_pdf_extension():
    validator = FileValidator()
    ok, msg = validator.validate("fake.pdf", "application/pdf", b"not a pdf")
    assert not ok
