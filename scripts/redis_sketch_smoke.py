import asyncio
import json
import os

from packages.core.cache.sketch_store import RedisSketchStore


async def main() -> None:
    os.environ["REDIS_URL"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    store = RedisSketchStore()
    await store.set("smoke", {"ok": True}, ttl_seconds=60)
    val = await store.get("smoke")
    print(json.dumps(val))


if __name__ == "__main__":
    asyncio.run(main())

