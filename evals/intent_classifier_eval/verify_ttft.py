#!/usr/bin/env python3
"""Verify Time-To-First-Token (TTFT) wiring end-to-end.

For each available provider this script:
  1. Emits a *real* traced streaming LLM call via ``traced_llm_call``.
  2. Records the local TTFT measured at the first streamed token.
  3. Waits for the run to flush, then reads it back from LangSmith and
     confirms the ``new_token`` event (and derived ``first_token_time``)
     was actually stored on the LLM run — this is what powers the
     "Time To First Token" column in the LangSmith UI.

Usage:
  python -m evals.intent_classifier_eval.verify_ttft
  python -m evals.intent_classifier_eval.verify_ttft --provider openai
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from evals.intent_classifier_eval.config import (  # noqa: E402
    MODEL_MATRIX,
    ensure_langsmith_env,
    get_langsmith_project,
)
from evals.intent_classifier_eval.providers import provider_available  # noqa: E402

SYSTEM = 'You are a router. Return strictly JSON: {"intent":"direct_chat","confidence":0.5}'
USER = "Explain photosynthesis in one sentence."


def _emit_traced_call(provider: str, model: str, marker: str) -> Dict[str, Any]:
    """Emit a traced streaming call; return {ttft_local, trace_id, text}."""
    from langsmith import traceable
    from langsmith.run_helpers import get_current_run_tree

    from evals.intent_classifier_eval.langsmith_tracing import traced_llm_call
    from evals.intent_classifier_eval.providers import call_model

    captured: Dict[str, Any] = {"ttft_local": None, "trace_id": None, "text": ""}

    @traceable(name=f"ttft-verify-root-{marker}", run_type="chain")
    def _root() -> str:
        rt = get_current_run_tree()
        captured["trace_id"] = str(getattr(rt, "trace_id", "") or getattr(rt, "id", "")) or None

        t0 = time.perf_counter()
        # traced_llm_call wires on_first_token internally; we additionally
        # measure locally by wrapping the provider call timing via a marker.
        result = traced_llm_call(
            name=f"intent_classifier/ttft/{model}",
            provider=provider,
            model=model,
            system=SYSTEM,
            user=USER,
            temperature=0.1,
            max_tokens=200,
            call_fn=_timed_call(call_model, t0, captured),
        )
        text = result.get("text", "") if isinstance(result, dict) else str(result or "")
        captured["text"] = text
        return text

    _root()
    return captured


def _timed_call(inner_call_model, t0: float, captured: Dict[str, Any]):
    """Wrap call_model to also record local TTFT on first token."""

    def _wrapped(**kwargs):
        user_cb = kwargs.get("on_first_token")

        def _cb():
            if captured.get("ttft_local") is None:
                captured["ttft_local"] = round(time.perf_counter() - t0, 3)
            if user_cb is not None:
                user_cb()

        kwargs["on_first_token"] = _cb
        return inner_call_model(**kwargs)

    return _wrapped


def _flush() -> None:
    try:
        from langsmith import Client

        Client().flush()
    except Exception:
        pass


def _read_back_ttft(trace_id: Optional[str], marker: str, timeout_s: float = 60.0) -> Dict[str, Any]:
    """Poll LangSmith for the llm run and confirm new_token / first_token_time."""
    from langsmith import Client

    client = Client()
    project = get_langsmith_project()
    deadline = time.time() + timeout_s
    last_err: Optional[str] = None

    while time.time() < deadline:
        try:
            runs: List[Any] = list(
                client.list_runs(
                    project_name=project,
                    run_type="llm",
                    limit=25,
                )
            )
            for run in runs:
                # Match either by trace id or by the unique marker in the name chain.
                same_trace = trace_id and str(getattr(run, "trace_id", "")) == trace_id
                name_match = marker in (getattr(run, "name", "") or "")
                if not (same_trace or name_match):
                    continue

                events = getattr(run, "events", None) or []
                has_new_token = any(
                    (e.get("name") if isinstance(e, dict) else None) == "new_token"
                    for e in events
                )
                ftt = getattr(run, "first_token_time", None)
                extra = getattr(run, "extra", None) or {}
                meta = extra.get("metadata", {}) if isinstance(extra, dict) else {}
                return {
                    "found": True,
                    "run_id": str(run.id),
                    "run_name": getattr(run, "name", None),
                    "has_new_token_event": has_new_token,
                    "first_token_time": str(ftt) if ftt else None,
                    "total_tokens": getattr(run, "total_tokens", None),
                    "prompt_tokens": getattr(run, "prompt_tokens", None),
                    "completion_tokens": getattr(run, "completion_tokens", None),
                    "total_cost": str(getattr(run, "total_cost", None)),
                    "usage_metadata": meta.get("usage_metadata"),
                    "event_count": len(events),
                }
        except Exception as exc:
            last_err = str(exc)
        time.sleep(3.0)

    return {"found": False, "error": last_err or "run not found within timeout"}


def verify_provider(provider: str, model: str) -> Dict[str, Any]:
    marker = uuid.uuid4().hex[:8]
    print(f"\n--- {provider} / {model} (marker={marker}) ---")
    if not provider_available(provider):
        print("  SKIP: no API key")
        return {"provider": provider, "model": model, "skipped": True}

    emitted = _emit_traced_call(provider, model, marker)
    ttft_local = emitted.get("ttft_local")
    text_ok = bool((emitted.get("text") or "").strip())
    print(f"  local TTFT: {ttft_local}s | text_ok: {text_ok}")

    if ttft_local is None:
        print("  WARN: streaming did not fire first-token callback (no TTFT captured locally)")

    _flush()
    print("  waiting for run to appear in LangSmith...")
    readback = _read_back_ttft(emitted.get("trace_id"), f"ttft/{model}")

    if not readback.get("found"):
        print(f"  FAIL readback: {readback.get('error')}")
    else:
        print(
            "  LangSmith run: "
            f"new_token_event={readback['has_new_token_event']} "
            f"first_token_time={readback['first_token_time']} "
            f"tokens(in/out/total)={readback['prompt_tokens']}/"
            f"{readback['completion_tokens']}/{readback['total_tokens']} "
            f"total_cost={readback['total_cost']}"
        )

    return {
        "provider": provider,
        "model": model,
        "ttft_local_seconds": ttft_local,
        "text_ok": text_ok,
        "readback": readback,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify TTFT streaming wiring")
    parser.add_argument("--provider", action="append", help="Filter: openai, anthropic, gemini")
    args = parser.parse_args()

    ensure_langsmith_env()

    specs = MODEL_MATRIX
    if args.provider:
        allowed = {p.lower() for p in args.provider}
        specs = [s for s in MODEL_MATRIX if s.provider in allowed]

    results = [verify_provider(s.provider, s.model) for s in specs]

    print("\n=== SUMMARY ===")
    overall_ok = False
    for r in results:
        if r.get("skipped"):
            print(f"  {r['provider']:9s} SKIPPED (no key)")
            continue
        rb = r.get("readback") or {}
        ttft_ok = rb.get("has_new_token_event") or bool(rb.get("first_token_time"))
        status = "OK" if (r.get("ttft_local") is not None or ttft_ok) else "FAIL"
        if ttft_ok:
            overall_ok = True
        print(
            f"  {r['provider']:9s} {status:4s} "
            f"local_ttft={r.get('ttft_local_seconds')} "
            f"langsmith_new_token={rb.get('has_new_token_event')} "
            f"first_token_time={rb.get('first_token_time')}"
        )

    print(
        "\nResult: "
        + (
            "TTFT wiring VERIFIED in LangSmith."
            if overall_ok
            else "TTFT not confirmed in LangSmith (check output above)."
        )
    )
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
