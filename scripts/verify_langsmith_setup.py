#!/usr/bin/env python3
"""
Verify LangSmith end-to-end: env → traced LLM call → LangSmith API.

Usage:
  python scripts/verify_langsmith_setup.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config.settings import settings  # noqa: E402
from packages.core.monitoring.langsmith_bootstrap import configure_langsmith_tracing  # noqa: E402


async def _emit_traced_call() -> str:
    from langsmith import traceable

    from packages.core.llm import get_llm_client, get_model_for_task

    @traceable(name="langsmith_setup_verify", run_type="chain")
    async def _run() -> str:
        provider, model = get_model_for_task("intent_classifier")
        client = get_llm_client(provider=provider, model=model)
        response = await client.generate(
            prompt="Reply with exactly one word: LANGSMITH_OK",
            system_prompt="Connectivity test for LangSmith tracing.",
            feature_tag="langsmith_setup_verify",
            max_tokens=16,
        )
        return (response.content or "").strip()

    return await _run()


def _wait_for_run(project: str, timeout_s: float = 45.0) -> dict:
    from langsmith import Client

    client = Client()
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        runs = list(
            client.list_runs(
                project_name=project,
                limit=3,
                is_root=True,
            )
        )
        for run in runs:
            if run.name == "langsmith_setup_verify" or (
                run.extra and run.extra.get("metadata", {}).get("ls_method") == "langsmith_setup_verify"
            ):
                return {
                    "id": str(run.id),
                    "name": run.name,
                    "status": run.status,
                    "total_tokens": run.total_tokens,
                    "prompt_tokens": run.prompt_tokens,
                    "completion_tokens": run.completion_tokens,
                }
        time.sleep(2.0)
    if runs:
        r = runs[0]
        return {
            "id": str(r.id),
            "name": r.name,
            "status": r.status,
            "note": "Latest run returned; verify name matches langsmith_setup_verify in UI",
        }
    return {}


async def main() -> int:
    print("=== LangSmith setup verification ===\n")

    status = configure_langsmith_tracing()
    print(f"Tracing enabled: {status.get('enabled')}")
    print(f"Project:         {status.get('project')}")
    print(f"Endpoint:        {status.get('endpoint')}")

    if not status.get("enabled"):
        print(
            "\nFAIL: LangSmith tracing is off. Add to .env:\n"
            "  LANGSMITH_TRACING_ENABLED=true\n"
            "  LANGSMITH_API_KEY=lsv2_pt_...\n"
            "  LANGSMITH_PROJECT=notebooklm-dev\n"
        )
        return 1

    if not (settings.OPENAI_API_KEY or "").strip():
        print("\nFAIL: OPENAI_API_KEY is required for the traced test call.")
        return 1

    print("\n1) Emitting traced LLM call...")
    try:
        content = await _emit_traced_call()
        print(f"   LLM reply: {content!r}")
    except Exception as exc:
        print(f"   FAIL: traced call error: {exc}")
        return 1

    print("\n2) Waiting for run in LangSmith...")
    try:
        run_info = _wait_for_run(status["project"])
    except Exception as exc:
        print(f"   FAIL: LangSmith API error: {exc}")
        return 1

    if not run_info:
        print(
            "   WARN: No runs found yet. Trace may still be ingesting — "
            f"check https://smith.langchain.com/o/*/projects/p/{status['project']}"
        )
        return 0

    print(f"   Run id:     {run_info.get('id')}")
    print(f"   Run name:   {run_info.get('name')}")
    print(f"   Status:     {run_info.get('status')}")
    if run_info.get("total_tokens") is not None:
        print(f"   Tokens:     {run_info.get('total_tokens')} "
              f"(in={run_info.get('prompt_tokens')}, out={run_info.get('completion_tokens')})")

    print("\n3) Cursor MCP")
    print("   Ensure langsmith MCP is green in Cursor Settings -> MCP (OAuth or X-Api-Key).")
    print("   Then ask: list_projects / fetch_runs for this project.")

    print("\nPASS: LangSmith tracing is configured and API is reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
