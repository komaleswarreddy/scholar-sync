#!/usr/bin/env python3
"""Smoke test: LangSmith auth, dataset, and provider/model pings."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from evals.intent_classifier_eval.config import (  # noqa: E402
    DATASET_NAME,
    MODEL_MATRIX,
    ensure_langsmith_env,
    get_langsmith_project,
)
from evals.intent_classifier_eval.evaluator_loader import parse_model_response  # noqa: E402
from evals.intent_classifier_eval.prompts import render_prompts  # noqa: E402
from evals.intent_classifier_eval.providers import call_model, provider_available  # noqa: E402

SMOKE_QUERY = {"query": "What is photosynthesis?"}


def smoke_langsmith() -> dict:
    ensure_langsmith_env()
    project = get_langsmith_project()
    try:
        from langsmith import Client

        client = Client()
        ds = client.read_dataset(dataset_name=DATASET_NAME)
        examples = list(client.list_examples(dataset_id=ds.id, limit=5))
        return {
            "ok": True,
            "project": project,
            "dataset": DATASET_NAME,
            "dataset_id": str(ds.id),
            "example_count_sample": len(examples),
        }
    except Exception as exc:
        return {"ok": False, "project": project, "error": str(exc)}


def smoke_provider(spec) -> dict:
    if not provider_available(spec.provider):
        return {
            "provider": spec.provider,
            "model": spec.model,
            "ok": False,
            "skipped": True,
            "reason": "API key missing",
        }
    system, user = render_prompts("v1", SMOKE_QUERY)
    raw = call_model(
        provider=spec.provider,
        model=spec.model,
        system=system,
        user=user,
        temperature=0.1,
        max_tokens=400,
    )
    parsed = parse_model_response(raw)
    return {
        "provider": spec.provider,
        "model": spec.model,
        "ok": bool(parsed.get("intent")),
        "raw_len": len(raw),
        "parsed_intent": parsed.get("intent"),
        "parsed_keys": sorted(parsed.keys()) if parsed else [],
    }


def main() -> int:
    results = {
        "langsmith": smoke_langsmith(),
        "providers": [smoke_provider(spec) for spec in MODEL_MATRIX],
    }
    print(json.dumps(results, indent=2))

    ls_ok = results["langsmith"].get("ok")
    any_provider = any(p.get("ok") for p in results["providers"])

    if not ls_ok:
        print("\nFAIL: LangSmith or dataset not ready", file=sys.stderr)
        return 1
    if not any_provider:
        print("\nFAIL: No provider returned valid JSON", file=sys.stderr)
        return 1
    failed = [p for p in results["providers"] if not p.get("ok") and not p.get("skipped")]
    if failed:
        print(f"\nWARN: {len(failed)} provider(s) failed (continuing with available providers)", file=sys.stderr)
    print("\nSmoke test PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
