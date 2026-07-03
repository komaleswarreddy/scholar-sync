"""
Measure API latency for login and common admin/student routes.

Usage:
    python scripts/debug_latency.py

Targets (warm pool, dev default tenant):
  - /health           < 100ms
  - POST login        < 800ms (bootstrap) / < 1200ms (DB user)
  - GET /auth/me      < 300ms
  - GET /admin/users  < 800ms (no Clerk)
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import settings

API = "http://127.0.0.1:8000"
HEADERS = {"x-tenant-id": "default"}
SLOW_MS = 1500


def ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def timed(name: str, fn) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    try:
        fn()
        elapsed = ms(t0)
        ok = elapsed < SLOW_MS
        flag = "OK" if ok else "SLOW"
        print(f"  [{flag}] {name}: {elapsed:.0f}ms")
        return ok, elapsed, ""
    except Exception as e:
        elapsed = ms(t0)
        print(f"  [ERR] {name}: {elapsed:.0f}ms — {e}")
        return False, elapsed, str(e)


def main() -> int:
    print("Latency debug — ScholarSync API")
    print(f"API: {API}")
    print(f"Threshold: {SLOW_MS}ms per call\n")

    results: list[tuple[str, float, bool]] = []
    admin_token: str | None = None

    with httpx.Client(base_url=API, timeout=30.0) as c:
        ok, t, _ = timed("GET /health", lambda: c.get("/health").raise_for_status())
        results.append(("health", t, ok))

        def login_admin():
            nonlocal admin_token
            r = c.post(
                "/api/v1/auth/login",
                json={
                    "username": settings.BOOTSTRAP_ADMIN_USERNAME,
                    "password": settings.BOOTSTRAP_ADMIN_PASSWORD,
                },
                headers=HEADERS,
            )
            r.raise_for_status()
            admin_token = r.json()["access_token"]

        ok, t, _ = timed("POST /auth/login (bootstrap)", login_admin)
        results.append(("bootstrap_login", t, ok))

        if not admin_token:
            return 1

        auth = {**HEADERS, "Authorization": f"Bearer {admin_token}"}

        ok, t, _ = timed(
            "GET /auth/me",
            lambda: c.get("/api/v1/auth/me", headers=auth).raise_for_status(),
        )
        results.append(("auth_me", t, ok))

        # Second call — should be faster (warm)
        ok, t, _ = timed(
            "GET /auth/me (warm)",
            lambda: c.get("/api/v1/auth/me", headers=auth).raise_for_status(),
        )
        results.append(("auth_me_warm", t, ok))

        ok, t, _ = timed(
            "GET /admin/users (warm)",
            lambda: c.get("/api/v1/admin/users", headers=auth).raise_for_status(),
        )
        results.append(("admin_users_warm", t, ok))

        ok, t, _ = timed(
            "GET /admin/accounts",
            lambda: c.get("/api/v1/admin/accounts", headers=auth).raise_for_status(),
        )
        results.append(("admin_accounts", t, ok))

        # Burst — simulates sidebar navigation firing parallel requests
        times: list[float] = []
        for i in range(5):
            t0 = time.perf_counter()
            c.get("/api/v1/auth/me", headers=auth).raise_for_status()
            times.append(ms(t0))
        p50 = statistics.median(times)
        print(f"  [---] GET /auth/me x5 burst: p50={p50:.0f}ms min={min(times):.0f}ms max={max(times):.0f}ms")
        results.append(("auth_me_burst_p50", p50, p50 < SLOW_MS))

    print("\n" + "=" * 50)
    failed = [r for r in results if not r[2]]
    if failed:
        print(f"FAILED ({len(failed)} slow/error):")
        for name, t, _ in failed:
            print(f"  - {name}: {t:.0f}ms")
        return 1
    print("All latency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
