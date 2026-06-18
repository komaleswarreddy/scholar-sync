#!/usr/bin/env python3
"""
Upload all tiered datasets to LangSmith with full metadata (idempotent).

Example:
  python scripts/upload_prompt_tiered_to_langsmith.py
  python scripts/upload_prompt_tiered_to_langsmith.py --agent intent_classifier
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from packages.core.config.model_registry import (
    get_candidate_models,
    get_evaluator_name,
    get_passing_threshold,
)
from packages.core.evaluation.datasets.loader import (
    dataset_version_hash,
    load_agent_dataset,
    load_manifest,
)
from packages.core.observability.langsmith_publish import ensure_tracing, get_langsmith_project


def _existing_example_ids(client, dataset_id: str) -> set:
    ids: set = set()
    try:
        for ex in client.list_examples(dataset_id=dataset_id):
            meta = getattr(ex, "metadata", None) or {}
            if isinstance(meta, dict) and meta.get("id"):
                ids.add(str(meta["id"]))
    except Exception:
        pass
    return ids


def upload_agent(agent_id: str, prefix: str = "nbm-prompt", *, force: bool = False) -> dict:
    status = ensure_tracing()
    if not status.get("enabled"):
        raise RuntimeError("LangSmith tracing disabled; set LANGSMITH_TRACING_ENABLED and LANGSMITH_API_KEY")

    from langsmith import Client

    client = Client()
    dataset_name = f"{prefix}-{agent_id}"
    records = load_agent_dataset(agent_id)
    ds_hash = dataset_version_hash(agent_id)
    evaluator = get_evaluator_name(agent_id)
    models = get_candidate_models(agent_id)
    threshold = get_passing_threshold(agent_id)
    project = get_langsmith_project()

    description = (
        f"ScholarSync tiered eval | agent={agent_id} | evaluator={evaluator} | "
        f"threshold={threshold} | models={','.join(models)} | hash={ds_hash} | "
        f"examples={len(records)} | project={project}"
    )

    try:
        ds = client.read_dataset(dataset_name=dataset_name)
        if force:
            client.delete_dataset(dataset_id=ds.id)
            ds = client.create_dataset(dataset_name=dataset_name, description=description)
    except Exception:
        ds = client.create_dataset(
            dataset_name=dataset_name,
            description=description,
            metadata={
                "agent_id": agent_id,
                "evaluator": evaluator,
                "passing_threshold": threshold,
                "models": models,
                "dataset_hash": ds_hash,
                "tiered_manifest": True,
            },
        )

    existing = set() if force else _existing_example_ids(client, str(ds.id))
    created = 0
    skipped = 0
    for rec in records:
        if rec.id in existing:
            skipped += 1
            continue
        client.create_example(
            inputs=rec.input,
            outputs=rec.expected_output,
            dataset_id=ds.id,
            metadata={
                "id": rec.id,
                "variation": rec.variation,
                "tags": rec.tags,
                "evaluator": evaluator,
                "agent_id": agent_id,
            },
        )
        created += 1

    return {
        "dataset_name": dataset_name,
        "dataset_id": str(ds.id),
        "created": created,
        "skipped": skipped,
        "total": len(records),
        "evaluator": evaluator,
        "models": models,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default=None, help="Single agent id; omit for all")
    parser.add_argument("--prefix", default="nbm-prompt")
    parser.add_argument("--force", action="store_true", help="Recreate dataset from scratch")
    args = parser.parse_args()

    results = []
    if args.agent:
        results.append(upload_agent(args.agent, args.prefix, force=args.force))
    else:
        for ds in load_manifest().get("datasets") or []:
            aid = ds["dataset_id"]
            print(f"Uploading {aid}...")
            results.append(upload_agent(aid, args.prefix, force=args.force))

    summary = {
        "project": get_langsmith_project(),
        "datasets_uploaded": len(results),
        "details": results,
    }
    out = ROOT / "evals" / "reports" / "langsmith_datasets_upload.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
