#!/usr/bin/env python3
"""
Quick OpenAI billing/quota sanity check.

What it does:
- Sends a tiny request to OpenAI using OPENAI_API_KEY from your environment.
- If it succeeds, billing/quota is active (at least for this model/endpoint).
- If it fails, it prints a human-readable diagnosis (invalid key vs billing/quota vs network).

Usage (PowerShell):
  $env:OPENAI_API_KEY="sk-..." ; python .\scripts\check_openai_billing.py
Optional:
  $env:OPENAI_MODEL="gpt-4o-mini"
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Tuple

import httpx
from dotenv import load_dotenv


OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def _classify_openai_error(status_code: int, payload: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (category, message).
    category: ok | billing_or_quota | invalid_key | forbidden | rate_limited | network | other
    """
    err = (payload or {}).get("error") or {}
    code = str(err.get("code") or "").lower()
    etype = str(err.get("type") or "").lower()
    msg = str(err.get("message") or payload or "").strip()

    text = f"{code} {etype} {msg}".lower()

    if status_code == 401:
        return ("invalid_key", msg or "Unauthorized (check OPENAI_API_KEY)")

    if status_code == 403:
        # Can be org restrictions, disabled project key, model access, etc.
        if "billing" in text or "payment" in text:
            return ("billing_or_quota", msg or "Forbidden due to billing/payment")
        return ("forbidden", msg or "Forbidden (key/project/model access restriction)")

    if status_code in (402,):
        return ("billing_or_quota", msg or "Payment required / billing not active")

    if status_code == 429:
        if "insufficient_quota" in text or "quota" in text or "billing" in text:
            return ("billing_or_quota", msg or "Quota exceeded / billing issue")
        return ("rate_limited", msg or "Rate limited")

    if "insufficient_quota" in text or "billing" in text or "payment" in text:
        return ("billing_or_quota", msg or "Billing/quota issue")

    return ("other", msg or f"HTTP {status_code}")


def _post_json(path: str, body: Dict[str, Any], api_key: str, timeout_s: float = 20.0) -> httpx.Response:
    url = OPENAI_BASE_URL.rstrip("/") + path
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    client_timeout = httpx.Timeout(timeout_s, connect=10.0)
    with httpx.Client(timeout=client_timeout) as client:
        return client.post(url, headers=headers, json=body)


def main() -> int:
    # Load .env from repo root/current working directory if present.
    # This avoids putting secrets into shell commands or logs.
    load_dotenv(override=False)

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        print("[FAIL] OPENAI_API_KEY is not set in your environment.")
        print("   PowerShell:  $env:OPENAI_API_KEY='sk-...'; python .\\scripts\\check_openai_billing.py")
        return 2

    model = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()

    # Prefer the modern Responses API. If the account/library doesn't support it, we fall back.
    attempts = [
        (
            "/v1/responses",
            {"model": model, "input": "ping"},
            "Responses API",
        ),
        (
            "/v1/chat/completions",
            {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 10,
                "temperature": 0,
            },
            "Chat Completions API",
        ),
    ]

    for path, body, label in attempts:
        try:
            res = _post_json(path, body, api_key)
        except httpx.TimeoutException as e:
            print(f"[FAIL] Network timeout calling {label} ({path}).")
            print(f"   Details: {e}")
            return 3
        except httpx.RequestError as e:
            print(f"[FAIL] Network error calling {label} ({path}).")
            print(f"   Details: {e}")
            return 3

        if 200 <= res.status_code < 300:
            print(f"[OK] OpenAI request succeeded via {label}.")
            print("   Billing/quota looks active for this key + model.")
            try:
                data = res.json()
                # Print minimal proof without dumping full content.
                rid = data.get("id") or data.get("response", {}).get("id")
                print(f"   response_id: {rid or '(no id)'}")
            except Exception:
                pass
            return 0

        # Try to parse error
        payload: Dict[str, Any] = {}
        try:
            payload = res.json()
        except Exception:
            payload = {"raw": (res.text or "").strip()}

        category, message = _classify_openai_error(res.status_code, payload)

        # If endpoint doesn't exist, fall through to next attempt.
        if res.status_code == 404:
            continue

        print(f"[FAIL] OpenAI request failed via {label} (HTTP {res.status_code}).")
        print(f"   Category: {category}")
        if message:
            print(f"   Message: {message}")
        else:
            print("   Message: (none)")
        print("   Raw error payload:")
        print(_pretty(payload))

        if category in ("billing_or_quota",):
            print("\nLikely cause: billing not active, no credits, or budget/quota exceeded.")
        elif category in ("invalid_key",):
            print("\nLikely cause: invalid/revoked API key, or key not from OpenAI Platform.")
        elif category in ("forbidden",):
            print("\nLikely cause: project/org restrictions or model access not enabled for this key.")

        return 1

    print("[FAIL] Both OpenAI endpoints returned 404.")
    print("   This usually means the base URL is wrong or the account is behind a proxy.")
    print(f"   OPENAI_BASE_URL={OPENAI_BASE_URL!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

