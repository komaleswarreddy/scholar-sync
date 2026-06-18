"""
Synchronous PDF validation at upload time.

Catches encrypted-password and obviously corrupt PDFs before background processing.
"""

from __future__ import annotations

import io
from typing import Optional

import pypdf

SCANNED_PDF_MESSAGE = (
    "This is an image-only PDF with no extractable text. "
    "Please upload a text-based PDF instead."
)

ENCRYPTED_PDF_NO_PASSWORD_MESSAGE = (
    "PDF is password-protected. Provide the pdf_password form field with the correct password."
)

ENCRYPTED_PDF_WRONG_PASSWORD_MESSAGE = (
    "Incorrect password for PDF. Please provide the correct password."
)


def validate_pdf_at_upload(file_content: bytes, pdf_password: Optional[str] = None) -> None:
    """
    Validate PDF readability at upload boundary.

    Raises ValueError with a user-readable message when the upload should be rejected.
    """
    if not file_content.startswith(b"%PDF"):
        raise ValueError("File does not appear to be a valid PDF.")

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_content))
    except Exception as exc:
        error_type = type(exc).__name__
        msg = str(exc)
        if error_type in {"PdfReadError", "PdfStreamError", "PdfParseError"} or "invalid" in msg.lower():
            raise ValueError(f"PDF file appears to be corrupted or invalid: {msg}") from exc
        raise ValueError(f"Failed to read PDF: {msg}") from exc

    if reader.is_encrypted:
        if not pdf_password:
            if not reader.decrypt(""):
                raise ValueError(ENCRYPTED_PDF_NO_PASSWORD_MESSAGE)
        elif not reader.decrypt(pdf_password):
            raise ValueError(ENCRYPTED_PDF_WRONG_PASSWORD_MESSAGE)


def is_image_only_pdf(file_content: bytes, pdf_password: Optional[str] = None) -> bool:
    """Return True when PDF opens but contains no extractable text."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_content))
    except Exception:
        return False

    if reader.is_encrypted:
        password = pdf_password or ""
        if not reader.decrypt(password):
            return False

    text_parts: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
        except Exception:
            continue
    return not "".join(text_parts).strip()
