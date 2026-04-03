import asyncio
import os

from redis.asyncio import Redis


async def main() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    prefix = os.getenv("REDIS_KEY_PREFIX", "ncert:doc_sketch:")
    r = Redis.from_url(url, decode_responses=True)
    keys = await r.keys(f"{prefix}*")
    print(f"keys={len(keys)}")
    for k in keys[:20]:
        ttl = await r.ttl(k)
        print(f"{k} ttl={ttl}")
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())

