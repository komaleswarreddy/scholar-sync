import asyncio
import json
import os

from redis.asyncio import Redis


async def main() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    prefix = os.getenv("REDIS_KEY_PREFIX", "ncert:doc_sketch:")
    key = os.getenv("SKETCH_KEY", "").strip()
    if not key:
        raise SystemExit("Set SKETCH_KEY to the content_hash value (without prefix).")

    r = Redis.from_url(url, decode_responses=True)
    redis_key = f"{prefix}{key}"
    raw = await r.get(redis_key)
    ttl = await r.ttl(redis_key)

    print(f"redis_key={redis_key}")
    print(f"ttl_seconds={ttl}")
    if not raw:
        print("value=None")
        await r.aclose()
        return

    try:
        obj = json.loads(raw)
    except Exception:
        print("value=<non-json>")
        print(raw[:4000])
        await r.aclose()
        return

    print("value=")
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:4000])
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())

