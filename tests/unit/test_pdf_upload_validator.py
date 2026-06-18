"""Unit tests for synchronous PDF upload validation (ING-03, ING-05)."""

import io

import pypdf
import pytest
from pypdf import PdfWriter

from packages.core.processing.pdf_upload_validator import validate_pdf_at_upload


def _encrypted_pdf_bytes(password: str = "secret") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_encrypted_pdf_without_password_raises():
    data = _encrypted_pdf_bytes("secret")
    with pytest.raises(ValueError, match="password-protected"):
        validate_pdf_at_upload(data, None)


def test_encrypted_pdf_with_correct_password_ok():
    data = _encrypted_pdf_bytes("secret")
    validate_pdf_at_upload(data, "secret")


def test_corrupt_pdf_raises():
    with pytest.raises(ValueError):
        validate_pdf_at_upload(b"%PDF truncated", None)
