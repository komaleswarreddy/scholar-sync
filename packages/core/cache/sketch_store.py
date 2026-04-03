from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from config.settings import settings

try:
    from redis.asyncio import Redis  # type: ignore
except Exception:  # pragma: no cover
    Redis = None  # type: ignore


class SketchStore(Protocol):
    def get(self, key: str) -> Optional[Dict[str, Any]]: ...

    def set(self, key: str, sketch: Dict[str, Any], ttl_seconds: int) -> None: ...


_redis_client: Optional["Redis"] = None


def _get_redis_client() -> Optional["Redis"]:
    global _redis_client
    if Redis is None:
        return None
    if _redis_client is not None:
        return _redis_client
    url = str(getattr(settings, "REDIS_URL", "") or "").strip()
    if not url:
        return None
    timeout_s = float(getattr(settings, "REDIS_TIMEOUT_S", 1.5))
    try:
        _redis_client = Redis.from_url(url, socket_timeout=timeout_s, socket_connect_timeout=timeout_s, decode_responses=True)
    except Exception:
        _redis_client = None
    return _redis_client


@dataclass(frozen=True)
class RedisSketchStore:
    """
    Redis-backed sketch store — used for NCERT and tenant upload document sketches.

    Keys are stored as: {key_prefix or REDIS_KEY_PREFIX}{optional_tenant_segment:}{key}
    When tenant_segment is set: {prefix}{tenant_segment}:{key} for isolation between tenants.
    Values are JSON strings of the sketch dict.
    """

    key_prefix: str = ""
    tenant_segment: str = ""

    def _k(self, key: str) -> str:
        pref = self.key_prefix or str(getattr(settings, "REDIS_KEY_PREFIX", "ncert:doc_sketch:"))
        seg = (self.tenant_segment or "").strip()
        safe_seg = "".join(ch for ch in seg if ch.isalnum() or ch in ("-", "_"))
        if safe_seg:
            return f"{pref}{safe_seg}:{key}"
        return f"{pref}{key}"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        r = _get_redis_client()
        if r is None:
            return None
        try:
            raw = await r.get(self._k(key))
            if not raw:
                return None
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    async def set(self, key: str, sketch: Dict[str, Any], ttl_seconds: int) -> None:
        r = _get_redis_client()
        if r is None:
            return
        try:
            await r.set(self._k(key), json.dumps(sketch, ensure_ascii=False), ex=max(1, int(ttl_seconds)))
        except Exception:
            return


@dataclass(frozen=True)
class DiskSketchStore:
    """
    Disk-backed sketch store (JSON files) — used for NCERT document sketches.

    Later this can be swapped for Redis by implementing the same SketchStore Protocol.
    """

    cache_dir: Path = Path("cache/ncert_global/sketch")

    def _path_for_key(self, key: str) -> Path:
        safe = "".join(ch for ch in (key or "").strip() if ch.isalnum() or ch in ("-", "_"))
        if not safe:
            safe = "unknown"
        return self.cache_dir / f"{safe}.json"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        p = self._path_for_key(key)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if not isinstance(obj, dict):
                return None
            expires_at = obj.get("expires_at")
            if expires_at is not None:
                try:
                    if float(expires_at) <= time.time():
                        return None
                except Exception:
                    pass
            sketch = obj.get("sketch")
            return sketch if isinstance(sketch, dict) else None
        except Exception:
            return None

    def set(self, key: str, sketch: Dict[str, Any], ttl_seconds: int) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        p = self._path_for_key(key)
        payload = {
            "version": 1,
            "key": key,
            "created_at": time.time(),
            "expires_at": time.time() + max(1, int(ttl_seconds)),
            "sketch": sketch,
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

