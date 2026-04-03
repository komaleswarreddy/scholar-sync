import asyncio
import os

from redis.asyncio import Redis


async def main() -> None:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = Redis.from_url(url, decode_responses=True)
    pong = await r.ping()
    print(f"redis_ping={pong}")
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())

