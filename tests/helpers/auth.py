"""Dev JWT helpers for local integration tests."""

from __future__ import annotations

import base64
import json


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def make_dev_jwt(sub: str = "integration_test_user") -> str:
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": sub}
    return (
        f"{_b64url(json.dumps(header).encode())}."
        f"{_b64url(json.dumps(payload).encode())}."
    )
