"""
File Validator

Validates uploaded files for security and format at the API boundary.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}

BLOCKED_EXTENSIONS = {
    ".exe",
    ".mp4",
    ".zip",
    ".docx",
    ".doc",
    ".xlsx",
    ".pptx",
    ".dll",
    ".bat",
    ".sh",
    ".js",
    ".html",
    ".svg",
}

BLOCKED_CONTENT_TYPE_PREFIXES = (
    "application/x-msdownload",
    "application/zip",
    "video/",
    "application/octet-stream",
)


class FileValidator:
    """Validates uploaded files before storage or background processing."""

    def __init__(self, max_size_bytes: int = 10 * 1024 * 1024):
        self.max_size_bytes = max_size_bytes

    def validate(
        self,
        filename: str,
        content_type: Optional[str],
        file_content: bytes,
    ) -> Tuple[bool, str]:
        if not file_content:
            return False, "File is empty"

        if len(file_content) > self.max_size_bytes:
            return False, f"File too large. Max is {self.max_size_bytes // (1024 * 1024)}MB."

        ext = os.path.splitext(filename or "")[1].lower()
        mime = (content_type or "").lower().strip()

        if ext in BLOCKED_EXTENSIONS:
            return False, f"File type '{ext}' is not supported. Only PDF, text, and image files are allowed."

        if mime and any(mime.startswith(prefix) for prefix in BLOCKED_CONTENT_TYPE_PREFIXES):
            if ext not in ALLOWED_EXTENSIONS:
                return False, f"File type '{mime}' is not supported. Only PDF, text, and image files are allowed."

        if ext and ext not in ALLOWED_EXTENSIONS:
            return False, "Only PDF, text, and image files are supported"

        if mime and mime not in ALLOWED_CONTENT_TYPES:
            if ext not in ALLOWED_EXTENSIONS:
                return False, "Only PDF, text, and image files are supported"

        if ext == ".pdf" and not file_content.startswith(b"%PDF"):
            return False, "File does not appear to be a valid PDF."

        if ext == ".txt":
            try:
                file_content.decode("utf-8")
            except UnicodeDecodeError:
                return False, "Text file must be valid UTF-8."

        return True, ""
