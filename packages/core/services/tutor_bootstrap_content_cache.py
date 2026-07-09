"""Redis + in-memory cache for the tutor first-open BOOTSTRAP CONTENT (chapter-scoped).

NCERT chapter content is identical for every student nationally, so the LLM-generated
opening summary / suggestions / studio recommendations (TutorNotebookPrepareService
step 1) and the generated study-asset JSON (step 2 — e.g. flashcards/quiz content) for
a given (class, subject, chapter, concept) scope can be safely reused across students
instead of re-running the full ~48s generation chain on every notebook open.

This mirrors the Redis-primary / in-memory-fallback pattern, client usage, and
tenant-scoped key style established in tutor_ncert_context_cache.py, so the two caches
behave consistently (same Redis client construction, same timeout handling, same
scoping granularity: class_num + subject + chapter_no + chapter_name + concept, plus
tenant_id in the key).

Safety note: this cache stores full JSON-serializable dicts (not a single string), and
callers (see tutor_notebook_prepare_service.py) are responsible for never placing
presigned/expiring URLs in the cached payload — only stable, non-expiring content.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

from config.settings import settings


def tutor_bootstrap_content_cache_key(scope: Dict[str, Any]) -> str:
    """Stable cache key for a tutor chapter scope.

    Same field set/granularity as tutor_ncert_context_cache_key for consistency.
    """
    parts = [
        str(scope.get("class_num") or ""),
        str(scope.get("subject_slug") or scope.get("subject_key") or ""),
        str(scope.get("chapter_no") or ""),
        str(scope.get("filter_chapter_name") or "").strip().lower(),
        str(scope.get("concept") or ""),
    ]
    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    prefix = getattr(
        settings, "TUTOR_BOOTSTRAP_CONTENT_REDIS_KEY_PREFIX", "tutor:bootstrap_content:"
    )
    return f"{prefix}{digest}"


class TutorBootstrapContentCache:
    """Chapter-scoped cache for the full tutor bootstrap payload (summary + assets).

    Stores a JSON-serializable dict shaped like:
        {
            "opening_summary": str,
            "suggestions": [...],
            "studio_recommendations": [...],
            "auto_types": [str, ...],
            "assets": {task_type: content_dict, ...},  # only cache-safe asset types
        }
    """

    _memory: Dict[str, Tuple[Dict[str, Any], float]] = {}

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def _ttl_seconds(self) -> int:
        return int(getattr(settings, "TUTOR_BOOTSTRAP_CONTENT_CACHE_TTL_SECONDS", 172800))

    def _redis_key(self, scope: Dict[str, Any]) -> str:
        return f"{self.tenant_id}:{tutor_bootstrap_content_cache_key(scope)}"

    async def get(self, scope: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = self._redis_key(scope)
        redis_val = await self._redis_get(key)
        if redis_val is not None:
            self._memory[key] = (redis_val, time.time() + self._ttl_seconds())
            return redis_val

        entry = self._memory.get(key)
        if not entry:
            return None
        data, expires_at = entry
        if time.time() >= expires_at:
            self._memory.pop(key, None)
            return None
        return data

    async def set(self, scope: Dict[str, Any], payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict) or not payload:
            return
        key = self._redis_key(scope)
        ttl = self._ttl_seconds()
        self._memory[key] = (payload, time.time() + ttl)
        await self._redis_set(key, payload, ttl)

    def _redis_timeout_seconds(self) -> float:
        return min(float(getattr(settings, "REDIS_TIMEOUT_S", 1.5)), 0.35)

    async def _redis_get(self, key: str) -> Optional[Dict[str, Any]]:
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
            return data if isinstance(data, dict) else None
        except Exception as exc:
            print(f"[TUTOR_BOOTSTRAP_CONTENT_CACHE] redis get failed: {exc}")
            return None

    async def _redis_set(self, key: str, payload: Dict[str, Any], ttl: int) -> None:
        url = getattr(settings, "REDIS_URL", "") or ""
        if not url.strip():
            return
        try:
            from redis.asyncio import Redis

            timeout = self._redis_timeout_seconds()
            client = Redis.from_url(url, socket_connect_timeout=timeout, socket_timeout=timeout)
            raw = json.dumps(payload)
            try:
                await asyncio.wait_for(client.set(key, raw, ex=ttl), timeout=timeout + 0.1)
            finally:
                await client.aclose()
        except Exception as exc:
            print(f"[TUTOR_BOOTSTRAP_CONTENT_CACHE] redis set failed: {exc}")
