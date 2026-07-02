#!/usr/bin/env python3
"""
check_api_credits.py

Pre-run credit check for all API providers used in LangSmith evals.
Uses the same raw HTTP calls as the eval harness (no SDK dependencies).
Run this BEFORE every agent eval to confirm credits are available.

Usage:
    python scripts/check_api_credits.py                          # check all 3 providers
    python scripts/check_api_credits.py --agent whole_file_reduce  # check only that agent's providers

Exit code 0 = all required providers OK (safe to run)
Exit code 1 = one or more providers have a hard credit/auth failure (stop, fix first)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

_TIMEOUT = 20


# ── OpenAI ────────────────────────────────────────────────────────────────

def check_openai() -> tuple[bool, str]:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return False, "AUTH ERROR — OPENAI_API_KEY not set in .env"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=_TIMEOUT)
    except Exception as e:
        return False, f"NETWORK ERROR — {str(e)[:120]}"

    if resp.status_code == 200:
        return True, "OK"

    msg = ""
    try:
        msg = resp.json().get("error", {}).get("message", resp.text[:200])
    except Exception:
        msg = resp.text[:200]

    if resp.status_code == 429:
        return False, f"QUOTA EXCEEDED (429) — {msg}"
    if resp.status_code == 401:
        return False, f"AUTH ERROR (401) — {msg}"
    if resp.status_code == 402:
        return False, f"PAYMENT REQUIRED (402) — {msg}"
    if "quota" in msg.lower() or "billing" in msg.lower() or "insufficient" in msg.lower():
        return False, f"QUOTA/BILLING ERROR ({resp.status_code}) — {msg}"
    return False, f"HTTP {resp.status_code} — {msg}"


# ── Anthropic ─────────────────────────────────────────────────────────────

def check_anthropic() -> tuple[bool, str]:
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        return False, "AUTH ERROR — ANTHROPIC_API_KEY not set in .env"

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}],
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=_TIMEOUT)
    except Exception as e:
        return False, f"NETWORK ERROR — {str(e)[:120]}"

    if resp.status_code == 200:
        return True, "OK"

    msg = ""
    try:
        data = resp.json()
        msg = data.get("error", {}).get("message", resp.text[:200])
    except Exception:
        msg = resp.text[:200]

    if resp.status_code == 429:
        return False, f"QUOTA EXCEEDED (429) — {msg}"
    if resp.status_code == 401:
        return False, f"AUTH ERROR (401) — {msg}"
    if resp.status_code == 400 and ("usage limits" in msg.lower() or "credit" in msg.lower()):
        return False, f"MONTHLY LIMIT REACHED (400) — {msg}"
    if "quota" in msg.lower() or "billing" in msg.lower() or "usage limits" in msg.lower():
        return False, f"QUOTA/BILLING ERROR ({resp.status_code}) — {msg}"
    return False, f"HTTP {resp.status_code} — {msg}"


# ── Gemini ────────────────────────────────────────────────────────────────

def check_gemini() -> tuple[bool, str]:
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()
    if not api_key:
        return False, "AUTH ERROR — GEMINI_API_KEY not set in .env"

    model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": "hi"}]}],
        "generationConfig": {"maxOutputTokens": 1},
    }
    try:
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=_TIMEOUT)
    except Exception as e:
        return False, f"NETWORK ERROR — {str(e)[:120]}"

    if resp.status_code == 200:
        return True, "OK"

    msg = ""
    try:
        data = resp.json()
        msg = (
            data.get("error", {}).get("message", "")
            or data.get("message", resp.text[:200])
        )
    except Exception:
        msg = resp.text[:200]

    if resp.status_code == 429 or "resource exhausted" in msg.lower():
        return False, f"QUOTA EXCEEDED (429) — {msg}"
    if resp.status_code in (503, 500) or "unavailable" in msg.lower():
        # Soft fail — harness auto-skips Gemini if health check fails
        return None, f"UNAVAILABLE ({resp.status_code}) — will be auto-skipped by harness"
    if resp.status_code == 401 or "api key" in msg.lower():
        return False, f"AUTH ERROR (401) — {msg}"
    if "quota" in msg.lower() or "billing" in msg.lower():
        return False, f"QUOTA/BILLING ERROR ({resp.status_code}) — {msg}"
    # Unknown error — treat as soft fail (Gemini harness will retry with its own health check)
    return None, f"UNKNOWN ({resp.status_code}) — {msg[:120]} — harness will decide at runtime"


# ── Provider registry ─────────────────────────────────────────────────────

PROVIDER_CHECKS = {
    "openai":    check_openai,
    "anthropic": check_anthropic,
    "gemini":    check_gemini,
}


# ── Detect which providers an agent needs ─────────────────────────────────

def providers_for_agent(agent_id: str) -> set[str]:
    models_path = ROOT / "evals" / "agent_eval" / "agent_models.json"
    if not models_path.exists():
        return set(PROVIDER_CHECKS.keys())
    data = json.loads(models_path.read_text(encoding="utf-8"))
    specs = data.get("agents", {}).get(agent_id, [])
    if not specs:
        return set(PROVIDER_CHECKS.keys())
    providers = {s["provider"] for s in specs if not s.get("skip_runtime", False)}
    # gemini is always attempted now (skip_runtime=false), include it
    providers.add("gemini")
    return providers


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-run API credit check")
    parser.add_argument("--agent", help="Agent ID — checks only providers that agent uses")
    parser.add_argument("--all", action="store_true", help="Check all 3 providers")
    args = parser.parse_args()

    if args.all or not args.agent:
        providers_to_check = list(PROVIDER_CHECKS.keys())
    else:
        providers_to_check = sorted(providers_for_agent(args.agent))

    print(f"\n{'='*62}")
    print(f"  API CREDIT PRE-CHECK")
    if args.agent:
        print(f"  Agent: {args.agent}")
    print(f"{'='*62}")

    results: dict[str, tuple] = {}
    for provider in providers_to_check:
        check_fn = PROVIDER_CHECKS.get(provider)
        if not check_fn:
            continue
        print(f"\n  Checking {provider.upper()}...", end=" ", flush=True)
        ok, msg = check_fn()
        results[provider] = (ok, msg)
        if ok is True:
            status = "PASS"
        elif ok is None:
            status = "WARN"
        else:
            status = "FAIL"
        print(f"[{status}] {msg}")

    print(f"\n{'='*62}")

    hard_failed = [p for p, (ok, _) in results.items() if ok is False]
    soft_warned  = [p for p, (ok, _) in results.items() if ok is None]
    passed       = [p for p, (ok, _) in results.items() if ok is True]

    if hard_failed:
        print(f"  STOP — DO NOT RUN EVAL")
        print(f"  Hard failures: {', '.join(p.upper() for p in hard_failed)}")
        for p in hard_failed:
            print(f"    [{p}] {results[p][1]}")
        if soft_warned:
            print(f"  Gemini warnings (soft — harness will auto-skip): {', '.join(soft_warned)}")
        print(f"{'='*62}\n")
        return 1

    if soft_warned:
        print(f"  PROCEED WITH CAUTION")
        print(f"  Passed: {', '.join(p.upper() for p in passed)}")
        print(f"  Gemini soft-warn: {', '.join(soft_warned)} (harness auto-skips if unhealthy)")
    else:
        print(f"  ALL PROVIDERS OK — safe to run eval")
        for p in passed:
            print(f"    [{p.upper()}] PASS")

    print(f"{'='*62}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
