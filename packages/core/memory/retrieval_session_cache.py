"""Redis + in-memory cache for last retrieved chunks (follow-up aware retrieval)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from config.settings import settings


def build_retrieval_session_key(
    *,
    chat_id: Optional[str],
    active_source_ids: Optional[List[str]],
    include_ncert_global: bool = False,
    ncert_class: Optional[int] = None,
    ncert_subject: Optional[str] = None,
    ncert_chapter_no: Optional[int] = None,
) -> str:
    """Stable session key for follow-up chunk reuse."""
    if chat_id and str(chat_id).strip():
        return f"chat:{str(chat_id).strip()}"
    parts = [
        "sources:" + ",".join(sorted(str(s) for s in (active_source_ids or []))),
        f"ncert:{int(include_ncert_global)}",
        f"class:{ncert_class or ''}",
        f"subj:{(ncert_subject or '').strip().lower()}",
        f"ch:{ncert_chapter_no or ''}",
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"scope:{digest}"


class RetrievalSessionCache:
    """Persists last selected retrieval matches across HTTP requests."""

    _memory: Dict[str, tuple[List[Dict[str, Any]], float]] = {}

    def __init__(self, tenant_id: str, user_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id or "anonymous"

    def _ttl_seconds(self) -> int:
        return int(getattr(settings, "RETRIEVAL_SESSION_CACHE_TTL_SECONDS", 3600))

    def _redis_key(self, session_key: str) -> str:
        prefix = getattr(settings, "RETRIEVAL_SESSION_REDIS_KEY_PREFIX", "retrieval:prev_chunks:")
        return f"{prefix}{self.tenant_id}:{self.user_id}:{session_key}"

    async def get_chunks(self, session_key: str) -> Optional[List[Dict[str, Any]]]:
        key = self._redis_key(session_key)
        redis_val = await self._redis_get(key)
        if redis_val is not None:
            self._memory[key] = (redis_val, time.time() + self._ttl_seconds())
            return redis_val

        entry = self._memory.get(key)
        if not entry:
            return None
        chunks, expires_at = entry
        if time.time() >= expires_at:
            self._memory.pop(key, None)
            return None
        return chunks

    async def set_chunks(self, session_key: str, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return
        key = self._redis_key(session_key)
        ttl = self._ttl_seconds()
        trimmed = chunks[: int(getattr(settings, "RETRIEVAL_SESSION_MAX_CHUNKS", 10))]
        self._memory[key] = (trimmed, time.time() + ttl)
        await self._redis_set(key, trimmed, ttl)

    def _redis_timeout_seconds(self) -> float:
        return min(float(getattr(settings, "REDIS_TIMEOUT_S", 1.5)), 0.35)

    async def _redis_get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        url = getattr(settings, "REDIS_URL", "") or ""
        if not url.strip():
            return None
        try:
            from redis.asyncio import Redis

            timeout = self._redis_timeout_seconds()
            client = Redis.from_url(url, socket_connect_timeout=timeout, socket_timeout=timeout)
            try:
                raw = await asyncio.wait_for(client.get(key), timeout=timeout + 0.1)
            finally:
                await client.aclose()
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            return None
        except Exception as exc:
            print(f"[RETRIEVAL_SESSION_CACHE] redis get failed: {exc}")
            return None

    async def _redis_set(self, key: str, chunks: List[Dict[str, Any]], ttl: int) -> None:
        url = getattr(settings, "REDIS_URL", "") or ""
        if not url.strip():
            return
        try:
            from redis.asyncio import Redis

            timeout = self._redis_timeout_seconds()
            client = Redis.from_url(url, socket_connect_timeout=timeout, socket_timeout=timeout)
            try:
                payload = json.dumps(chunks, ensure_ascii=False)
                await asyncio.wait_for(client.setex(key, ttl, payload), timeout=timeout + 0.1)
            finally:
                await client.aclose()
        except Exception as exc:
            print(f"[RETRIEVAL_SESSION_CACHE] redis set failed: {exc}")
