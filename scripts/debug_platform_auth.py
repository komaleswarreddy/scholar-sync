"""
End-to-end smoke test for platform auth and admin account CRUD.

Usage:
    python scripts/debug_platform_auth.py
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings import settings

API_BASE = "http://127.0.0.1:8000"
TENANT_HEADER = {"x-tenant-id": "default"}
TEST_USERNAME = f"debug_{uuid.uuid4().hex[:8]}"
TEST_PASSWORD = "testpass123"


class Check:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.results: list[tuple[str, bool, str]] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.passed += 1
        self.results.append((name, True, detail))
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name: str, detail: str) -> None:
        self.failed += 1
        self.results.append((name, False, detail))
        print(f"  FAIL  {name} — {detail}")

    def summary(self) -> int:
        print("\n" + "=" * 60)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        for name, success, detail in self.results:
            status = "OK" if success else "ERR"
            print(f"  [{status}] {name}: {detail}")
        print("=" * 60)
        return 0 if self.failed == 0 else 1


def main() -> int:
    check = Check()
    print("Platform Auth & Admin CRUD Debug")
    print(f"API: {API_BASE}")
    print(f"Bootstrap user: {settings.BOOTSTRAP_ADMIN_USERNAME}")
    print()

    admin_token: str | None = None
    created_id: str | None = None

    with httpx.Client(base_url=API_BASE, timeout=60.0) as client:
        # 1. Health
        try:
            r = client.get("/health")
            if r.status_code == 200:
                check.ok("health", r.json().get("status", "ok"))
            else:
                check.fail("health", f"status {r.status_code}")
        except httpx.ConnectError:
            check.fail("health", "Cannot connect — start API with uvicorn on port 8000")
            return check.summary()

        # 2. Bootstrap admin login
        r = client.post(
            "/api/v1/auth/login",
            json={
                "username": settings.BOOTSTRAP_ADMIN_USERNAME,
                "password": settings.BOOTSTRAP_ADMIN_PASSWORD,
            },
            headers=TENANT_HEADER,
        )
        if r.status_code == 200:
            data = r.json()
            admin_token = data.get("access_token")
            user = data.get("user", {})
            if admin_token and user.get("role") == "schooladmin":
                check.ok("bootstrap login", f"role={user.get('role')}")
            else:
                check.fail("bootstrap login", json.dumps(data)[:200])
        else:
            check.fail("bootstrap login", f"{r.status_code} {r.text[:300]}")

        if not admin_token:
            return check.summary()

        auth_headers = {**TENANT_HEADER, "Authorization": f"Bearer {admin_token}"}

        # 3. GET /auth/me
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        if r.status_code == 200 and r.json().get("is_bootstrap_admin"):
            check.ok("auth/me", "bootstrap admin confirmed")
        else:
            check.fail("auth/me", f"{r.status_code} {r.text[:200]}")

        # 4. CREATE account
        r = client.post(
            "/api/v1/admin/accounts",
            json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
                "role": "student",
                "first_name": "Debug",
                "last_name": "Student",
                "email": f"{TEST_USERNAME}@test.local",
                "institute": "Test Institute",
                "class_level": "Class 11",
            },
            headers=auth_headers,
        )
        if r.status_code == 201:
            created = r.json()
            created_id = created.get("id")
            check.ok("create account", f"id={created_id}, username={TEST_USERNAME}")
        else:
            check.fail("create account", f"{r.status_code} {r.text[:300]}")

        # 5. LIST accounts
        r = client.get(
            "/api/v1/admin/accounts",
            params={"search": TEST_USERNAME},
            headers=auth_headers,
        )
        if r.status_code == 200:
            items = r.json().get("items", [])
            found = any(i.get("username") == TEST_USERNAME for i in items)
            if found:
                check.ok("list accounts", f"found {TEST_USERNAME}")
            else:
                check.fail("list accounts", f"user not in list ({len(items)} items)")
        else:
            check.fail("list accounts", f"{r.status_code} {r.text[:200]}")

        # 6. UPDATE account
        if created_id:
            r = client.patch(
                f"/api/v1/admin/accounts/{created_id}",
                json={
                    "first_name": "Updated",
                    "class_level": "Class 12",
                    "institute": "Updated Institute",
                },
                headers=auth_headers,
            )
            if r.status_code == 200 and r.json().get("first_name") == "Updated":
                check.ok("update account", "profile fields updated")
            else:
                check.fail("update account", f"{r.status_code} {r.text[:200]}")

        # 7. Student login
        r = client.post(
            "/api/v1/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            headers=TENANT_HEADER,
        )
        student_token: str | None = None
        if r.status_code == 200:
            data = r.json()
            student_token = data.get("access_token")
            if student_token and data.get("user", {}).get("role") == "student":
                check.ok("student login", f"username={TEST_USERNAME}")
            else:
                check.fail("student login", json.dumps(data)[:200])
        else:
            check.fail("student login", f"{r.status_code} {r.text[:200]}")

        # 8. Student profile read + update
        if student_token:
            student_headers = {**TENANT_HEADER, "Authorization": f"Bearer {student_token}"}
            r = client.get("/api/v1/users/me/profile", headers=student_headers)
            if r.status_code == 200 and r.json().get("username") == TEST_USERNAME:
                check.ok("student profile read", r.json().get("institute", ""))
            else:
                check.fail("student profile read", f"{r.status_code} {r.text[:200]}")

            r = client.patch(
                "/api/v1/users/me/profile",
                json={"mobile": "9876543210"},
                headers=student_headers,
            )
            if r.status_code == 200 and r.json().get("mobile") == "9876543210":
                check.ok("student profile update", "mobile set")
            else:
                check.fail("student profile update", f"{r.status_code} {r.text[:200]}")

        # 9. Soft deactivate (delete equivalent)
        if created_id:
            r = client.patch(
                f"/api/v1/admin/accounts/{created_id}",
                json={"is_active": False},
                headers=auth_headers,
            )
            if r.status_code == 200 and r.json().get("is_active") is False:
                check.ok("deactivate account", "is_active=false")
            else:
                check.fail("deactivate account", f"{r.status_code} {r.text[:200]}")

            r = client.post(
                "/api/v1/auth/login",
                json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
                headers=TENANT_HEADER,
            )
            if r.status_code == 401:
                check.ok("deactivated login blocked", "401 as expected")
            else:
                check.fail("deactivated login blocked", f"expected 401, got {r.status_code}")

        # 10. Non-admin denied
        if student_token:
            r = client.get(
                "/api/v1/admin/accounts",
                headers={**TENANT_HEADER, "Authorization": f"Bearer {student_token}"},
            )
            if r.status_code == 403:
                check.ok("student admin access denied", "403 as expected")
            else:
                check.fail("student admin access denied", f"expected 403, got {r.status_code}")

    return check.summary()


if __name__ == "__main__":
    raise SystemExit(main())
