"""
End-to-end latency debugger for ScholarSync API + DB.

Measures cold vs warm paths for login, profile, student home, and admin routes.
Run with API server up: python -m uvicorn apps.api.main:app --reload --port 8000

Usage:
    python scripts/debug_latency.py
    python scripts/debug_latency.py --api http://127.0.0.1:8000 --username sync@gmail.com --password '***'
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import settings

DEFAULT_API = "http://127.0.0.1:8000"
HEADERS = {"x-tenant-id": "default"}

THRESHOLDS_MS = {
    "health": 500,
    "bootstrap_login": 25000,  # cold Supabase TLS + pool can spike on first query
    "bootstrap_login_warm": 2000,
    "db_login": 5000,
    "auth_me": 800,
    "auth_me_warm": 400,
    "home_summary": 2500,
    "notebooks": 2000,
    "admin_users": 2000,
    "admin_accounts": 2000,
    "burst_p50": 600,
}


def ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def timed(name: str, fn: Callable[[], None], threshold: float) -> tuple[bool, float, str]:
    t0 = time.perf_counter()
    try:
        fn()
        elapsed = ms(t0)
        ok = elapsed <= threshold
        flag = "OK" if ok else "SLOW"
        print(f"  [{flag}] {name}: {elapsed:.0f}ms (budget {threshold:.0f}ms)")
        return ok, elapsed, ""
    except Exception as e:
        elapsed = ms(t0)
        print(f"  [ERR] {name}: {elapsed:.0f}ms - {e}")
        return False, elapsed, str(e)


def check_api_reachable(client: httpx.Client) -> bool:
    try:
        r = client.get("/health", timeout=5.0)
        return r.status_code == 200
    except Exception as e:
        print(f"\n[FAIL] API not reachable at {client.base_url}: {e}")
        print("Start backend: python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="ScholarSync latency debugger")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--username", default="", help="DB user login (optional)")
    parser.add_argument("--password", default="", help="DB user password (optional)")
    args = parser.parse_args()

    print("=" * 60)
    print("ScholarSync latency debugger")
    print(f"API: {args.api}")
    print("=" * 60)

    results: list[tuple[str, float, bool]] = []
    token: str | None = None

    with httpx.Client(base_url=args.api, timeout=45.0) as client:
        if not check_api_reachable(client):
            return 2

        ok, t, _ = timed("GET /health", lambda: client.get("/health").raise_for_status(), THRESHOLDS_MS["health"])
        results.append(("health", t, ok))

        def login_bootstrap():
            nonlocal token
            r = client.post(
                "/api/v1/auth/login",
                json={
                    "username": settings.BOOTSTRAP_ADMIN_USERNAME,
                    "password": settings.BOOTSTRAP_ADMIN_PASSWORD,
                },
                headers=HEADERS,
            )
            r.raise_for_status()
            token = r.json()["access_token"]

        ok, t, _ = timed("POST /auth/login (bootstrap)", login_bootstrap, THRESHOLDS_MS["bootstrap_login"])
        results.append(("bootstrap_login", t, ok))

        if not token:
            return 1

        auth = {**HEADERS, "Authorization": f"Bearer {token}"}

        def login_bootstrap_warm():
            r = client.post(
                "/api/v1/auth/login",
                json={
                    "username": settings.BOOTSTRAP_ADMIN_USERNAME,
                    "password": settings.BOOTSTRAP_ADMIN_PASSWORD,
                },
                headers=HEADERS,
            )
            r.raise_for_status()

        ok, t, _ = timed(
            "POST /auth/login (bootstrap warm)",
            login_bootstrap_warm,
            THRESHOLDS_MS["bootstrap_login_warm"],
        )
        results.append(("bootstrap_login_warm", t, ok))

        for label, path, key in [
            ("GET /auth/me (cold)", "/api/v1/auth/me", "auth_me"),
            ("GET /auth/me (warm)", "/api/v1/auth/me", "auth_me_warm"),
            ("GET /home/summary", "/api/v1/home/summary", "home_summary"),
            ("GET /notebooks", "/api/v1/notebooks", "notebooks"),
            ("GET /admin/users", "/api/v1/admin/users", "admin_users"),
            ("GET /admin/accounts", "/api/v1/admin/accounts", "admin_accounts"),
        ]:
            ok, t, _ = timed(
                label,
                lambda p=path: client.get(p, headers=auth).raise_for_status(),
                THRESHOLDS_MS[key],
            )
            results.append((key if "warm" not in label else "auth_me_warm", t, ok))

        if args.username and args.password:
            def login_db_user():
                r = client.post(
                    "/api/v1/auth/login",
                    json={"username": args.username, "password": args.password},
                    headers=HEADERS,
                )
                r.raise_for_status()

            ok, t, _ = timed("POST /auth/login (db user)", login_db_user, THRESHOLDS_MS["db_login"])
            results.append(("db_login", t, ok))

        times: list[float] = []
        for _ in range(8):
            t0 = time.perf_counter()
            client.get("/api/v1/auth/me", headers=auth).raise_for_status()
            times.append(ms(t0))
        p50 = statistics.median(times)
        burst_ok = p50 <= THRESHOLDS_MS["burst_p50"]
        print(
            f"  [{'OK' if burst_ok else 'SLOW'}] GET /auth/me x8 burst: "
            f"p50={p50:.0f}ms min={min(times):.0f}ms max={max(times):.0f}ms "
            f"(budget {THRESHOLDS_MS['burst_p50']:.0f}ms)"
        )
        results.append(("burst_p50", p50, burst_ok))

        print("\n--- Session sync chain (login -> /auth/me -> /home/summary) ---")
        sync_token: str | None = None
        sync_user: dict = {}

        def login_sync_chain():
            nonlocal sync_token, sync_user
            r = client.post(
                "/api/v1/auth/login",
                json={
                    "username": settings.BOOTSTRAP_ADMIN_USERNAME,
                    "password": settings.BOOTSTRAP_ADMIN_PASSWORD,
                },
                headers=HEADERS,
            )
            r.raise_for_status()
            data = r.json()
            sync_token = data["access_token"]
            sync_user = data.get("user") or {}
            assert sync_token, "missing access_token"
            assert sync_user.get("id"), "login response missing user.id"

        ok, t, _ = timed("login->user payload", login_sync_chain, 3000)
        results.append(("login_user_payload", t, ok))

        if sync_token:
            sync_auth = {**HEADERS, "Authorization": f"Bearer {sync_token}"}
            me_data: dict = {}

            def fetch_me():
                nonlocal me_data
                r = client.get("/api/v1/auth/me", headers=sync_auth)
                r.raise_for_status()
                me_data = r.json()

            ok, t, _ = timed("login->/auth/me id match", fetch_me, 800)
            id_match = me_data.get("id") == sync_user.get("id")
            if not id_match:
                print(f"  [ERR] user id mismatch: login={sync_user.get('id')} me={me_data.get('id')}")
            else:
                print(f"  [OK] user id match: {me_data.get('id')}")
            results.append(("login_me_id_match", t, ok and id_match))

            ok, t, _ = timed(
                "login->/home/summary",
                lambda: client.get("/api/v1/home/summary", headers=sync_auth).raise_for_status(),
                THRESHOLDS_MS["home_summary"],
            )
            results.append(("login_home_summary", t, ok))

    print("\n" + "=" * 60)
    failed = [r for r in results if not r[2]]
    if failed:
        print(f"FAILED ({len(failed)} checks):")
        for name, t, _ in failed:
            print(f"  - {name}: {t:.0f}ms")
        print("\nCommon fixes:")
        print("  1. Ensure API is running and DATABASE_URL uses Supabase port 6543 (transaction pooler)")
        print("  2. Restart API after changes — warm_db_pool runs on startup")
        print("  3. Avoid running heavy seed/migration scripts while testing UI")
        print("  4. Frontend default timeout is 25s; login uses 30s")
        return 1

    print("All latency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
