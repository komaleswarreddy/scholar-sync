#!/usr/bin/env python3
"""
Run intent classifier LangSmith experiments: prompt x model matrix.

Usage:
  python -m evals.intent_classifier_eval.run_eval
  python -m evals.intent_classifier_eval.run_eval --prompt v1 --provider openai
  python -m evals.intent_classifier_eval.run_eval --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from evals.intent_classifier_eval.config import (  # noqa: E402
    AGENT_ID,
    DATASET_NAME,
    MODEL_MATRIX,
    PROMPT_VERSIONS,
    ModelSpec,
    ensure_langsmith_env,
    get_langsmith_project,
)
from evals.intent_classifier_eval.evaluator_loader import (  # noqa: E402
    get_per_example_evaluators,
    get_summary_evaluators,
    parse_model_response,
)
from evals.intent_classifier_eval.llm_judge import routing_judge  # noqa: E402
from evals.intent_classifier_eval.prompts import render_prompts  # noqa: E402
from evals.intent_classifier_eval.providers import call_model, provider_available  # noqa: E402

REPORTS_DIR = ROOT / "evals" / "reports" / "intent_classifier_langsmith"
STEP_CHECKPOINT = REPORTS_DIR / "step_checkpoint.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _safe_prefix(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in text)[:80]


def _max_tokens_for_spec(spec: ModelSpec) -> int:
    if spec.provider.lower() == "openai" and "gpt-5" in spec.model.lower():
        return 1200
    return 400


def make_target_fn(prompt_version: str, spec: ModelSpec):
    """Closure for LangSmith evaluate target."""

    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timezone

        from langsmith.run_helpers import get_current_run_tree

        from evals.intent_classifier_eval.langsmith_tracing import traced_llm_call
        from evals.intent_classifier_eval.providers import call_model

        root_run = get_current_run_tree()

        def _mirror_first_token() -> None:
            if root_run is None:
                return
            try:
                root_run.add_event(
                    {
                        "name": "new_token",
                        "time": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception:
                pass

        system, user = render_prompts(prompt_version, inputs)
        llm_result = traced_llm_call(
            name=f"intent_classifier/{prompt_version}/{spec.model}",
            provider=spec.provider,
            model=spec.model,
            system=system,
            user=user,
            temperature=0.1,
            max_tokens=_max_tokens_for_spec(spec),
            call_fn=call_model,
            on_first_token_extra=_mirror_first_token,
            json_mode=spec.provider.lower() == "openai",
        )
        return parse_model_response(
            llm_result.get("text", ""),
            refusal=llm_result.get("refusal"),
            finish_reason=llm_result.get("finish_reason"),
        )

    return target


def _resolve_data(client: Any, limit: Optional[int], offset: Optional[int] = None):
    """Return the dataset name, or a deterministic slice of examples.

    - No limit and no offset -> evaluate the whole dataset (pass the name).
    - limit/offset set -> fetch all examples, order them deterministically
      (created_at, then id), and return the slice [offset : offset+limit].

    Slicing keeps trace volume under LangSmith plan quotas and lets you cover
    the dataset incrementally (e.g. --offset 0 --limit 10, then --offset 10 ...).
    """
    off = offset or 0
    if (not limit or limit <= 0) and off <= 0:
        return DATASET_NAME

    ds = client.read_dataset(dataset_name=DATASET_NAME)
    examples = list(client.list_examples(dataset_id=ds.id))
    examples.sort(key=lambda e: (str(getattr(e, "created_at", "")), str(e.id)))

    if off < 0:
        off = 0
    if limit and limit > 0:
        return examples[off : off + limit]
    return examples[off:]


def run_single_experiment(
    client: Any,
    *,
    prompt_version: str,
    spec: ModelSpec,
    dry_run: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    experiment_prefix = _safe_prefix(f"ic-{prompt_version}-{spec.label}")
    metadata = {
        "agent_id": AGENT_ID,
        "prompt_version": prompt_version,
        "provider": spec.provider,
        "model": spec.model,
        "dataset": DATASET_NAME,
        "eval_harness": "intent_classifier_eval",
    }
    if limit and limit > 0:
        metadata["example_limit"] = limit
    if offset and offset > 0:
        metadata["example_offset"] = offset

    if dry_run:
        return {
            "experiment_prefix": experiment_prefix,
            "prompt_version": prompt_version,
            "provider": spec.provider,
            "model": spec.model,
            "example_limit": limit or 0,
            "example_offset": offset or 0,
            "status": "dry_run",
        }

    target = make_target_fn(prompt_version, spec)
    per_example = get_per_example_evaluators() + [routing_judge]
    summary = get_summary_evaluators()
    data = _resolve_data(client, limit, offset)

    import os as _os

    concurrency = int(_os.environ.get("INTENT_EVAL_CONCURRENCY", "2"))

    t0 = time.perf_counter()
    result = client.evaluate(
        target,
        data=data,
        evaluators=per_example,
        summary_evaluators=summary,
        experiment_prefix=experiment_prefix,
        metadata=metadata,
        max_concurrency=max(1, concurrency),
    )
    elapsed_s = time.perf_counter() - t0

    experiment_name = getattr(result, "experiment_name", None) or str(result)
    summary_row: Dict[str, Any] = {
        "experiment_prefix": experiment_prefix,
        "prompt_version": prompt_version,
        "provider": spec.provider,
        "model": spec.model,
        "elapsed_seconds": round(elapsed_s, 2),
        "experiment_name": experiment_name,
        "langsmith_url": _compare_url(experiment_name),
        "compare_url": _compare_url(experiment_name),
    }

    _attach_summary_from_result(summary_row, result)
    return summary_row


def _compare_url(experiment_name: str) -> Optional[str]:
    """Dataset compare URL with selectedSessions (clickable in Excel/Sheets)."""
    try:
        from langsmith import Client

        from evals.intent_classifier_eval.config import DATASET_NAME

        tenant_id = _resolve_tenant_id()
        if not tenant_id:
            return None
        client = Client()
        proj = client.read_project(project_name=experiment_name)
        session_id = str(proj.id)
        ds_id = str(getattr(proj, "reference_dataset_id", "") or "")
        if not ds_id:
            ds_id = str(client.read_dataset(dataset_name=DATASET_NAME).id)
        return (
            f"https://smith.langchain.com/o/{tenant_id}/datasets/{ds_id}"
            f"/compare?selectedSessions={session_id}"
        )
    except Exception:
        return None


def _experiment_url(experiment_name: str) -> Optional[str]:
    return _compare_url(experiment_name)


def _resolve_tenant_id() -> Optional[str]:
    """Best-effort lookup of the active workspace/tenant id for the API key."""
    try:
        import os

        import requests

        key = (os.environ.get("LANGSMITH_API_KEY") or "").strip()
        endpoint = (
            os.environ.get("LANGSMITH_ENDPOINT")
            or "https://api.smith.langchain.com"
        ).rstrip("/")
        if not key:
            return None
        resp = requests.get(
            f"{endpoint}/workspaces",
            headers={"x-api-key": key},
            timeout=15,
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0].get("id")
    except Exception:
        pass
    return None


def _attach_summary_from_result(row: Dict[str, Any], result: Any) -> None:
    """Parse severity_tier_summary fields embedded in comment by wrapper."""
    try:
        summaries = getattr(result, "summary_results", None) or []
        for sr in summaries:
            payload = sr if isinstance(sr, dict) else getattr(sr, "__dict__", {})
            key = payload.get("key") if isinstance(payload, dict) else getattr(sr, "key", None)
            if key != "severity_tier_summary":
                continue
            comment = str(payload.get("comment") if isinstance(payload, dict) else getattr(sr, "comment", ""))
            row["severity_score"] = payload.get("score") if isinstance(payload, dict) else getattr(sr, "score", None)
            if "ship_recommendation=" in comment:
                import re

                m = re.search(r"ship_recommendation=\"?([A-Z]+)\"?", comment)
                if m:
                    row["ship_recommendation"] = m.group(1)
            if "tier_0_blocking_count=" in comment:
                import re

                m = re.search(r"tier_0_blocking_count=(\d+)", comment)
                if m:
                    row["tier_0_blocking_count"] = int(m.group(1))
            if "tier_1_serious_rate=" in comment:
                import re

                m = re.search(r"tier_1_serious_rate=([0-9.]+)", comment)
                if m:
                    row["tier_1_serious_rate"] = float(m.group(1))
            row["severity_comment"] = comment[:2000]
    except Exception:
        pass


def run_matrix(
    *,
    prompts: Optional[List[str]] = None,
    models: Optional[List[ModelSpec]] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    ensure_langsmith_env()
    project = get_langsmith_project()

    prompt_list = list(prompts or PROMPT_VERSIONS)
    model_list = list(models or MODEL_MATRIX)

    # Filter unavailable providers
    active_models = [m for m in model_list if provider_available(m.provider)]
    skipped = [m.label for m in model_list if m not in active_models]

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "langsmith_project": project,
        "dataset": DATASET_NAME,
        "prompt_versions": prompt_list,
        "example_limit": limit or 0,
        "example_offset": offset or 0,
        "experiments": [],
        "skipped_providers": skipped,
        "dry_run": dry_run,
    }

    if dry_run:
        for pv in prompt_list:
            for spec in active_models:
                report["experiments"].append(
                    run_single_experiment(None, prompt_version=pv, spec=spec, dry_run=True, limit=limit, offset=offset)
                )
        return report

    from langsmith import Client

    client = Client()
    for pv in prompt_list:
        for spec in active_models:
            logger.info("Running experiment prompt=%s model=%s (%s)", pv, spec.model, spec.provider)
            try:
                row = run_single_experiment(client, prompt_version=pv, spec=spec, limit=limit, offset=offset)
                report["experiments"].append(row)
            except Exception as exc:
                logger.error("Experiment failed prompt=%s model=%s: %s", pv, spec.model, exc)
                report["experiments"].append({
                    "prompt_version": pv,
                    "provider": spec.provider,
                    "model": spec.model,
                    "status": "error",
                    "error": str(exc),
                })

    ok_count = sum(
        1 for e in report["experiments"]
        if e.get("ship_recommendation") == "OK"
    )
    report["summary"] = {
        "total_experiments": len(report["experiments"]),
        "ship_ok_count": ok_count,
        "pass_rate": round(ok_count / max(len(report["experiments"]), 1), 3),
    }
    return report


def _experiment_key(prompt_version: str, spec: ModelSpec) -> str:
    return f"{prompt_version}::{spec.provider}::{spec.model}"


def _build_plan(prompt_list: List[str], active_models: List[ModelSpec]):
    """Ordered list of (prompt_version, spec): prompt outer, model inner."""
    plan = []
    for pv in prompt_list:
        for spec in active_models:
            plan.append((pv, spec))
    return plan


def _load_checkpoint() -> Dict[str, Any]:
    if STEP_CHECKPOINT.exists():
        try:
            return json.loads(STEP_CHECKPOINT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"completed": {}, "started_at": datetime.now(timezone.utc).isoformat()}


def _save_checkpoint(ckpt: Dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STEP_CHECKPOINT.write_text(json.dumps(ckpt, indent=2), encoding="utf-8")


def run_stepwise(
    *,
    prompts: Optional[List[str]] = None,
    models: Optional[List[ModelSpec]] = None,
    status_only: bool = False,
) -> int:
    """Run ONE pending experiment per invocation (all 63 examples), then stop.

    Progress is checkpointed so re-running the same command continues with the
    next prompt x model combination until the whole matrix is complete.
    """
    ensure_langsmith_env()
    project = get_langsmith_project()

    prompt_list = list(prompts or PROMPT_VERSIONS)
    model_list = list(models or MODEL_MATRIX)
    active_models = [m for m in model_list if provider_available(m.provider)]
    skipped = [m.label for m in model_list if m not in active_models]

    plan = _build_plan(prompt_list, active_models)
    total = len(plan)
    ckpt = _load_checkpoint()
    completed: Dict[str, Any] = ckpt.get("completed", {})

    done_count = sum(1 for pv, spec in plan if _experiment_key(pv, spec) in completed)
    pending = [(pv, spec) for pv, spec in plan if _experiment_key(pv, spec) not in completed]

    # Always show where we are.
    print("=" * 64)
    print(f"STEP MODE  |  project={project}  |  progress={done_count}/{total}")
    if skipped:
        print(f"skipped providers (no API key): {', '.join(skipped)}")
    print("-" * 64)
    for idx, (pv, spec) in enumerate(plan, 1):
        key = _experiment_key(pv, spec)
        mark = "[x]" if key in completed else "[ ]"
        nxt = "  <-- NEXT" if (pending and (pv, spec) == pending[0]) else ""
        print(f" {mark} {idx:2d}. {pv:3s}  {spec.provider:10s} {spec.model}{nxt}")
    print("=" * 64)

    if status_only:
        return 0

    if not pending:
        print("\nAll experiments complete. Nothing to run.")
        print("Use --reset to start a fresh pass.")
        _write_stepwise_report(project, plan, completed, skipped)
        return 0

    pv, spec = pending[0]
    key = _experiment_key(pv, spec)
    print(f"\nRunning experiment {done_count + 1}/{total}: prompt={pv} model={spec.model} ({spec.provider})")
    print("Covering all 63 examples. Please wait...\n")

    from langsmith import Client

    client = Client()
    try:
        row = run_single_experiment(client, prompt_version=pv, spec=spec)
    except Exception as exc:
        logger.error("Experiment failed prompt=%s model=%s: %s", pv, spec.model, exc)
        print(f"\nExperiment FAILED: {exc}")
        print("Fix the issue and re-run the same command to retry this experiment.")
        return 1

    completed[key] = row
    ckpt["completed"] = completed
    ckpt["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_checkpoint(ckpt)

    new_done = done_count + 1
    print("\n" + "-" * 64)
    print(f"DONE {new_done}/{total}: {pv} / {spec.model}")
    if row.get("langsmith_url"):
        print(f"View: {row['langsmith_url']}")
    remaining = total - new_done
    if remaining > 0:
        nxt_pv, nxt_spec = pending[1]
        print(f"\nNEXT ({remaining} left): prompt={nxt_pv} model={nxt_spec.model} ({nxt_spec.provider})")
        print("Trigger it by running the SAME command again:")
        print("  python -m evals.intent_classifier_eval.run_eval --step")
    else:
        print("\nAll experiments complete!")
        _write_stepwise_report(project, plan, completed, skipped)
    print("-" * 64)
    return 0


def _write_stepwise_report(project, plan, completed, skipped) -> None:
    rows = [completed[_experiment_key(pv, spec)] for pv, spec in plan if _experiment_key(pv, spec) in completed]
    ok_count = sum(1 for e in rows if e.get("ship_recommendation") == "OK")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "langsmith_project": project,
        "dataset": DATASET_NAME,
        "mode": "stepwise",
        "experiments": rows,
        "skipped_providers": skipped,
        "summary": {
            "total_experiments": len(rows),
            "ship_ok_count": ok_count,
            "pass_rate": round(ok_count / max(len(rows), 1), 3),
        },
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"stepwise_matrix_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nFull leaderboard report written to {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Intent classifier LangSmith eval matrix")
    parser.add_argument("--prompt", action="append", help="Prompt version(s), e.g. v1")
    parser.add_argument("--provider", action="append", help="Filter provider: openai, anthropic, gemini")
    parser.add_argument("--model", action="append", help="Filter model id(s), e.g. gpt-5-mini")
    parser.add_argument("--dry-run", action="store_true", help="List experiments without running")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap examples per experiment (keeps traces under LangSmith plan quota)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="Skip the first N examples (use with --limit to cover the dataset in batches, e.g. --offset 10 --limit 10)",
    )
    parser.add_argument(
        "--step",
        action="store_true",
        help="Step mode: run ONE prompt x model experiment (all 63 examples) per invocation, "
             "then pause. Re-run the same command to continue the next until all 12 are done.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show step-mode progress (which experiments are done / pending) without running.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the step-mode checkpoint to start a fresh full pass.",
    )
    parser.add_argument("--output", default=None, help="Report JSON path")
    args = parser.parse_args()

    prompts = args.prompt or list(PROMPT_VERSIONS)
    models = MODEL_MATRIX
    if args.provider:
        allowed = {p.lower() for p in args.provider}
        models = [m for m in models if m.provider in allowed]
    if args.model:
        allowed_models = {m.lower() for m in args.model}
        models = [m for m in models if m.model.lower() in allowed_models]

    if args.reset:
        if STEP_CHECKPOINT.exists():
            STEP_CHECKPOINT.unlink()
            print(f"Checkpoint cleared: {STEP_CHECKPOINT}")
        else:
            print("No checkpoint to clear.")
        if not (args.step or args.status):
            return 0

    if args.step or args.status:
        return run_stepwise(prompts=prompts, models=models, status_only=args.status)

    report = run_matrix(prompts=prompts, models=models, dry_run=args.dry_run, limit=args.limit, offset=args.offset)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.output) if args.output else REPORTS_DIR / f"matrix_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
