"""Redis + in-memory cache for tutor NCERT context blocks (chapter-scoped)."""



from __future__ import annotations



import asyncio

import hashlib

import json

import time

from typing import Any, Callable, Dict, Optional, Tuple



from config.settings import settings





def tutor_ncert_context_cache_key(scope: Dict[str, Any]) -> str:

    """Stable cache key for a tutor chapter scope."""

    parts = [

        str(scope.get("class_num") or ""),

        str(scope.get("subject_slug") or scope.get("subject_key") or ""),

        str(scope.get("chapter_no") or ""),

        str(scope.get("filter_chapter_name") or "").strip().lower(),

        str(scope.get("concept") or ""),

    ]

    raw = "|".join(parts)

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    prefix = getattr(settings, "TUTOR_NCERT_CONTEXT_REDIS_KEY_PREFIX", "tutor:ncert_context:")

    return f"{prefix}{digest}"





class TutorNcertContextCache:

    """Chapter-scoped NCERT context cache with Redis primary and in-memory fallback."""



    _memory: Dict[str, Tuple[str, float]] = {}

    _inflight: Dict[str, asyncio.Task[str]] = {}



    def __init__(self, tenant_id: str):

        self.tenant_id = tenant_id



    def _ttl_seconds(self) -> int:

        return int(getattr(settings, "TUTOR_NCERT_CONTEXT_CACHE_TTL_SECONDS", 3600))



    def _redis_key(self, scope: Dict[str, Any]) -> str:

        return f"{self.tenant_id}:{tutor_ncert_context_cache_key(scope)}"



    async def get(self, scope: Dict[str, Any]) -> Optional[str]:

        key = self._redis_key(scope)

        redis_val = await self._redis_get(key)

        if redis_val:

            self._memory[key] = (redis_val, time.time() + self._ttl_seconds())

            return redis_val



        entry = self._memory.get(key)

        if not entry:

            return None

        context, expires_at = entry

        if time.time() >= expires_at:

            self._memory.pop(key, None)

            return None

        return context



    async def set(self, scope: Dict[str, Any], context: str) -> None:

        if not (context or "").strip():

            return

        key = self._redis_key(scope)

        ttl = self._ttl_seconds()

        self._memory[key] = (context, time.time() + ttl)

        await self._redis_set(key, context, ttl)



    async def get_or_fetch(

        self,

        scope: Dict[str, Any],

        fetch_fn: Callable[[], Any],

    ) -> Tuple[str, bool]:

        """Return (context, cache_hit)."""

        cached = await self.get(scope)

        if cached:

            return cached, True



        key = self._redis_key(scope)

        inflight = self._inflight.get(key)

        if inflight is not None:

            try:

                context = await inflight

                return context, True

            except Exception:

                pass



        task = asyncio.create_task(self._fetch_and_store(scope, fetch_fn))

        self._inflight[key] = task

        try:

            context = await task

            return context, False

        finally:

            self._inflight.pop(key, None)



    async def _fetch_and_store(

        self,

        scope: Dict[str, Any],

        fetch_fn: Callable[[], Any],

    ) -> str:

        context = await fetch_fn()

        if (context or "").strip():

            await self.set(scope, context)

        return context or ""



    async def warm(self, scope: Dict[str, Any], fetch_fn: Callable[[], Any]) -> Dict[str, Any]:

        """Prefetch and store context; returns metadata for the warm endpoint."""

        t0 = time.perf_counter()

        context, hit = await self.get_or_fetch(scope, fetch_fn)

        return {

            "cached": hit,

            "context_chars": len(context or ""),

            "duration_ms": int((time.perf_counter() - t0) * 1000),

        }



    def _redis_timeout_seconds(self) -> float:

        return min(float(getattr(settings, "REDIS_TIMEOUT_S", 1.5)), 0.35)



    async def _redis_get(self, key: str) -> Optional[str]:

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

            return str(data.get("context") or "")

        except Exception as exc:

            print(f"[TUTOR_NCERT_CACHE] redis get failed: {exc}")

            return None



    async def _redis_set(self, key: str, context: str, ttl: int) -> None:

        url = getattr(settings, "REDIS_URL", "") or ""

        if not url.strip():

            return

        try:

            from redis.asyncio import Redis



            timeout = self._redis_timeout_seconds()

            client = Redis.from_url(url, socket_connect_timeout=timeout, socket_timeout=timeout)

            payload = json.dumps({"context": context})

            try:

                await asyncio.wait_for(client.setex(key, ttl, payload), timeout=timeout + 0.1)

            finally:

                await client.aclose()

        except Exception as exc:

            print(f"[TUTOR_NCERT_CACHE] redis set failed: {exc}")


