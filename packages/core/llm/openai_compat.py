"""
OpenAI/httpx compatibility helpers.

This repo currently runs with OpenAI SDK versions that can conflict with newer
httpx proxy handling. Passing explicit httpx clients avoids the SDK building
its own client with unsupported proxy kwargs.
"""

from __future__ import annotations

from typing import Optional, Tuple

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None


def build_openai_http_clients(
    timeout_s: float = 60.0,
) -> Tuple[Optional["httpx.Client"], Optional["httpx.AsyncClient"]]:
    """
    Create explicit sync/async httpx clients for OpenAI and LlamaIndex.

    We intentionally disable environment-derived proxy settings because they can
    trigger OpenAI/httpx compatibility issues in some installed version pairs.
    """
    if httpx is None:  # pragma: no cover
        return None, None

    timeout = httpx.Timeout(timeout_s)
    sync_client = httpx.Client(timeout=timeout, trust_env=False)
    async_client = httpx.AsyncClient(timeout=timeout, trust_env=False)
    return sync_client, async_client
