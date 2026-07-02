#!/usr/bin/env python3
"""
Run multi-agent LangSmith bake-off matrix (14 agents; intent_classifier unchanged).

Usage:
  python -m evals.agent_eval.run_matrix --status
  python -m evals.agent_eval.run_matrix --step
  python -m evals.agent_eval.run_matrix --step --agent query_rewriter
  python -m evals.agent_eval.run_matrix --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from evals.agent_eval.config import (  # noqa: E402
    PROMPT_VERSIONS,
    SKIP_PROVIDERS_AT_RUNTIME,
    STRUCTURED_JSON_AGENT_IDS,
    ModelSpec,
    dataset_name,
    ensure_langsmith_env,
    get_agent_models,
    get_langsmith_project,
)
from evals.agent_eval.evaluator_loader import (  # noqa: E402
    get_per_example_evaluators,
    get_summary_evaluators,
    parse_model_response,
)
from evals.agent_eval.prompts import render_prompts  # noqa: E402
from evals.agent_eval.rate_limit_guard import (  # noqa: E402
    RateLimitAbort,
    count_session_traces,
    preflight,
    record_experiment,
)
from evals.agent_eval.registry import get_agent_spec, list_scope_agents  # noqa: E402
from evals.intent_classifier_eval.providers import call_model, provider_available  # noqa: E402

REPORTS_DIR = ROOT / "evals" / "reports" / "agent_matrix"
STEP_CHECKPOINT = REPORTS_DIR / "step_checkpoint.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Per-agent max_tokens defaults (long outputs for studio/RAG)
MAX_TOKENS_BY_AGENT: Dict[str, int] = {
    "query_rewriter": 1200,
    "query_decomposer": 1200,
    "scope_narrower": 1200,
    "rag_chat_response_generator": 1200,
    "studio_quiz": 2000,
    "studio_flashcards": 2000,
    "studio_mind_map": 2000,
    "studio_slide_deck": 2000,
    "studio_system_json": 1500,
    "chat_summarizer": 800,
    "hallucination_guard_retry": 600,
    # whole_file_reduce emits Markdown final_answer; gold answers reach 400-440 words
    # (~520-570 tokens). 600-token default truncates output mid-sentence causing low
    # word count, dependency_integrity failures, and schema_validity 0.5 scores.
    "whole_file_reduce": 1500,
    # whole_file_map_summarizer emits per-section Markdown summaries; can be multi-section.
    "whole_file_map_summarizer": 1500,
    # Problem-solving coaches emit a long 7-section coach_json; the 600 default
    # truncates the JSON mid-output -> parse fails -> every evaluator scores 0.
    # problem_dna_analyzer outputs a deeply nested DNA JSON (subject/chapter/conceptTags/
    # expert_solution_internal with key_steps[]) that routinely needs 1500-3000 tokens.
    "problem_dna_analyzer": 3000,
    "explain_from_basics": 8000,
    "show_best_approach": 8000,
    "show_missing_idea": 2000,
    "ncert_document_sketch": 1500,
    "help_me_solve_it": 2000,
    "problem_solver_followup": 2000,
    "tutor_notebook_bootstrap": 2000,
    "tutor_follow_up_questions": 800,
    "source_question_extraction": 2000,
    "image_ocr": 2000,
    "diagram_label_ocr": 1500,
}


def _safe_prefix(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in text)[:80]


def _max_tokens(agent_id: str) -> int:
    return MAX_TOKENS_BY_AGENT.get(agent_id, 600)


def make_target_fn(agent_id: str, prompt_version: str, spec: ModelSpec):
    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timezone

        from langsmith.run_helpers import get_current_run_tree

        from evals.intent_classifier_eval.langsmith_tracing import traced_llm_call

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

        system, user = render_prompts(agent_id, prompt_version, inputs)
        use_json = (
            spec.provider.lower() == "openai" and agent_id in STRUCTURED_JSON_AGENT_IDS
        )
        llm_result = traced_llm_call(
            name=f"{agent_id}/{prompt_version}/{spec.model}",
            provider=spec.provider,
            model=spec.model,
            system=system,
            user=user,
            temperature=0.1,
            max_tokens=_max_tokens(agent_id),
            call_fn=call_model,
            on_first_token_extra=_mirror_first_token,
            json_mode=use_json,
        )
        raw_text = (
            llm_result.get("text", "")
            if isinstance(llm_result, dict)
            else str(llm_result or "")
        )
        refusal = llm_result.get("refusal") if isinstance(llm_result, dict) else None
        finish_reason = (
            llm_result.get("finish_reason") if isinstance(llm_result, dict) else None
        )
        return parse_model_response(
            agent_id,
            raw_text,
            refusal=refusal,
            finish_reason=finish_reason,
        )

    return target


def _resolve_data(client: Any, agent_id: str, limit: Optional[int], offset: Optional[int] = None):
    ds_name = dataset_name(agent_id)
    off = offset or 0
    if (not limit or limit <= 0) and off <= 0:
        return ds_name

    ds = client.read_dataset(dataset_name=ds_name)
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
    agent_id: str,
    prompt_version: str,
    spec: ModelSpec,
    dry_run: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    experiment_prefix = _safe_prefix(f"ae-{agent_id}-{prompt_version}-{spec.label}")
    metadata = {
        "agent_id": agent_id,
        "prompt_version": prompt_version,
        "provider": spec.provider,
        "model": spec.model,
        "dataset": dataset_name(agent_id),
        "eval_harness": "agent_eval",
    }
    if limit and limit > 0:
        metadata["example_limit"] = limit
    if offset and offset > 0:
        metadata["example_offset"] = offset

    if dry_run:
        return {
            "agent_id": agent_id,
            "experiment_prefix": experiment_prefix,
            "prompt_version": prompt_version,
            "provider": spec.provider,
            "model": spec.model,
            "example_limit": limit or 0,
            "example_offset": offset or 0,
            "status": "dry_run",
        }

    target = make_target_fn(agent_id, prompt_version, spec)
    per_example = get_per_example_evaluators(agent_id)
    summary = get_summary_evaluators(agent_id)
    data = _resolve_data(client, agent_id, limit, offset)

    # LangSmith bills every ROOT run as a trace. One client.evaluate() run
    # creates traces in TWO places:
    #   1. The experiment session: 1 root run per example (the agent/model call).
    #   2. The auto-created "evaluators" project: 1 root run per evaluator
    #      invocation -> (n_examples * num_per_example_evaluators) + num_summary.
    # Total billable traces = target_traces + evaluator_traces.
    if isinstance(data, list):
        n_examples = len(data)
    else:
        try:
            n_examples = get_agent_spec(agent_id).example_count
        except Exception:
            n_examples = 0
    n_examples = max(int(n_examples), 1)
    n_per_eval = len(per_example or [])
    n_summary = len(summary or [])
    target_traces = n_examples
    evaluator_traces = n_examples * n_per_eval + n_summary
    estimated_traces = target_traces + evaluator_traces

    # --- RATE-LIMIT GUARD: abort BEFORE creating any trace if it could breach cap ---
    guard = preflight(
        client,
        agent_id=agent_id,
        prompt_version=prompt_version,
        model=spec.model,
        estimated_traces=estimated_traces,
    )
    print(
        f"[GUARD] month={guard['month']} used={guard['used_before']}/{guard['limit']} "
        f"margin={guard['safety_margin']} remaining={guard['remaining_before']} "
        f"| this run ~{estimated_traces} traces "
        f"({target_traces} agent + {evaluator_traces} evaluator "
        f"[{n_examples}x{n_per_eval}+{n_summary}]) "
        f"| workspace_in_reject_set={guard['workspace_in_reject_set']}"
    )

    import os as _os

    concurrency = int(_os.environ.get("AGENT_EVAL_CONCURRENCY", "2"))

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

    # --- RATE-LIMIT GUARD: measure ACTUAL traces created + update monthly ledger ---
    # Count the agent runs in the experiment session directly; the evaluator
    # traces are deterministic (n_examples * n_per_eval + n_summary), so we add
    # them to the measured agent count for the true billable total.
    measured_target = count_session_traces(client, experiment_name, expected=target_traces)
    measured_total = max(measured_target, target_traces) + evaluator_traces
    ledger = record_experiment(
        agent_id=agent_id,
        prompt_version=prompt_version,
        model=spec.model,
        experiment_name=experiment_name,
        measured_traces=measured_total,
        estimated_traces=estimated_traces,
    )
    used = int(ledger["used"])
    remaining_after = int(ledger["limit"]) - int(ledger["safety_margin"]) - used
    print(
        f"[GUARD] DONE: traces_this_experiment={measured_total} "
        f"(agent={max(measured_target, target_traces)} + evaluator={evaluator_traces}) "
        f"| monthly_used={used}/{ledger['limit']} (incl. margin {ledger['safety_margin']}) "
        f"| usable_remaining={remaining_after}"
    )

    summary_row: Dict[str, Any] = {
        "agent_id": agent_id,
        "experiment_prefix": experiment_prefix,
        "prompt_version": prompt_version,
        "provider": spec.provider,
        "model": spec.model,
        "elapsed_seconds": round(elapsed_s, 2),
        "experiment_name": experiment_name,
        "langsmith_url": _experiment_url(),
        "traces_this_experiment": measured_total,
        "traces_agent": max(measured_target, target_traces),
        "traces_evaluator": evaluator_traces,
        "traces_estimated": estimated_traces,
        "traces_used_month": used,
        "traces_limit": int(ledger["limit"]),
        "traces_usable_remaining": remaining_after,
    }
    _attach_summary_from_result(summary_row, result)
    return summary_row


def _experiment_url() -> Optional[str]:
    try:
        tenant_id = _resolve_tenant_id()
        if tenant_id:
            return f"https://smith.langchain.com/o/{tenant_id}/projects/p/{get_langsmith_project()}"
    except Exception:
        pass
    return None


def _resolve_tenant_id() -> Optional[str]:
    try:
        import os

        import requests

        key = (os.environ.get("LANGSMITH_API_KEY") or "").strip()
        endpoint = (
            os.environ.get("LANGSMITH_ENDPOINT") or "https://api.smith.langchain.com"
        ).rstrip("/")
        if not key:
            return None
        resp = requests.get(f"{endpoint}/workspaces", headers={"x-api-key": key}, timeout=15)
        if resp.status_code >= 400:
            return None
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0].get("id")
    except Exception:
        pass
    return None


def _attach_summary_from_result(row: Dict[str, Any], result: Any) -> None:
    try:
        summaries = getattr(result, "summary_results", None) or []
        for sr in summaries:
            payload = sr if isinstance(sr, dict) else getattr(sr, "__dict__", {})
            key = payload.get("key") if isinstance(payload, dict) else getattr(sr, "key", None)
            comment = str(
                payload.get("comment") if isinstance(payload, dict) else getattr(sr, "comment", "")
            )
            if "ship_recommendation" in comment or key and "severity" in str(key).lower():
                row["severity_score"] = (
                    payload.get("score") if isinstance(payload, dict) else getattr(sr, "score", None)
                )
                import re

                m = re.search(r"ship_recommendation=\"?([A-Z]+)\"?", comment)
                if m:
                    row["ship_recommendation"] = m.group(1)
                m = re.search(r"tier_0_blocking_count=(\d+)", comment)
                if m:
                    row["tier_0_blocking_count"] = int(m.group(1))
                m = re.search(r"tier_1_serious_rate=([0-9.]+)", comment)
                if m:
                    row["tier_1_serious_rate"] = float(m.group(1))
                row["severity_comment"] = comment[:2000]
    except Exception:
        pass


# Cache Gemini health results per model so we only probe each model once.
_GEMINI_HEALTH: Dict[str, bool] = {}


def _gemini_model_healthy(model: str) -> bool:
    """Fast pre-flight probe for a Gemini model.

    One tiny request, short timeout, NO retries — so a missing key, bad model
    name, auth error, or exhausted quota is detected in seconds and the model is
    skipped without burning LangSmith traces or waiting on backoff.
    """
    if model in _GEMINI_HEALTH:
        return _GEMINI_HEALTH[model]
    import os as _os

    import requests as _rq

    key = (
        _os.environ.get("GEMINI_API_KEY") or _os.environ.get("GOOGLE_API_KEY") or ""
    ).strip()
    if not key:
        _GEMINI_HEALTH[model] = False
        print(f"[GEMINI] fast-skip {model}: no GEMINI_API_KEY/GOOGLE_API_KEY")
        return False

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 8},
    }
    try:
        resp = _rq.post(url, params={"key": key}, json=body, timeout=12)
        ok = resp.status_code < 400
        if not ok:
            print(f"[GEMINI] fast-skip {model}: HTTP {resp.status_code} {resp.text[:140]}")
        else:
            print(f"[GEMINI] healthy: {model}")
        _GEMINI_HEALTH[model] = ok
        return ok
    except Exception as exc:
        print(f"[GEMINI] fast-skip {model}: {str(exc)[:140]}")
        _GEMINI_HEALTH[model] = False
        return False


def _active_models(agent_id: str) -> Tuple[List[ModelSpec], List[str]]:
    model_list = get_agent_models(agent_id)
    active: List[ModelSpec] = []
    skipped: List[str] = []
    for m in model_list:
        prov = m.provider.lower()
        if prov in ("deepseek", "unknown") or prov in SKIP_PROVIDERS_AT_RUNTIME:
            skipped.append(m.label)
            continue
        if not provider_available(m.provider):
            skipped.append(f"{m.label} (no api key)")
            continue
        if prov in ("gemini", "google") and not _gemini_model_healthy(m.model):
            skipped.append(f"{m.label} (gemini fast-skip)")
            continue
        active.append(m)
    return active, skipped


def _experiment_key(agent_id: str, prompt_version: str, spec: ModelSpec) -> str:
    return f"{agent_id}::{prompt_version}::{spec.provider}::{spec.model}"


def _is_done(completed: Dict[str, Any], key: str) -> bool:
    row = completed.get(key)
    if not row:
        return False
    return row.get("status") != "error"


def _matches_model_filter(spec: ModelSpec, models: Optional[List[str]]) -> bool:
    if not models:
        return True
    want = {m.lower().strip() for m in models}
    return spec.model.lower() in want or spec.label.lower() in want


def _filter_active_models(
    active: List[ModelSpec], models: Optional[List[str]]
) -> List[ModelSpec]:
    if not models:
        return active
    return [m for m in active if _matches_model_filter(m, models)]


def _build_plan(
    agent_ids: List[str],
    prompt_list: List[str],
    models: Optional[List[str]] = None,
) -> List[Tuple[str, str, ModelSpec]]:
    plan: List[Tuple[str, str, ModelSpec]] = []
    for agent_id in agent_ids:
        active, _ = _active_models(agent_id)
        active = _filter_active_models(active, models)
        for pv in prompt_list:
            for spec in active:
                plan.append((agent_id, pv, spec))
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
    agent_ids: Optional[List[str]] = None,
    prompts: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    status_only: bool = False,
) -> int:
    ensure_langsmith_env()
    project = get_langsmith_project()

    agents = list(agent_ids or list_scope_agents())
    prompt_list = list(prompts or PROMPT_VERSIONS)
    plan = _build_plan(agents, prompt_list, models)
    total = len(plan)
    ckpt = _load_checkpoint()
    completed: Dict[str, Any] = ckpt.get("completed", {})

    done_count = sum(1 for a, pv, spec in plan if _is_done(completed, _experiment_key(a, pv, spec)))
    pending = [(a, pv, spec) for a, pv, spec in plan if not _is_done(completed, _experiment_key(a, pv, spec))]

    print("=" * 72)
    print(f"AGENT EVAL STEP MODE | project={project} | progress={done_count}/{total}")
    print("intent_classifier: use evals.intent_classifier_eval.run_eval (unchanged)")
    print("-" * 72)
    for idx, (agent_id, pv, spec) in enumerate(plan, 1):
        key = _experiment_key(agent_id, pv, spec)
        mark = "[x]" if _is_done(completed, key) else "[ ]"
        nxt = "  <-- NEXT" if (pending and (agent_id, pv, spec) == pending[0]) else ""
        print(f" {mark} {idx:3d}. {agent_id:32s} {pv:3s} {spec.provider:10s} {spec.model}{nxt}")
    print("=" * 72)

    if status_only:
        return 0

    if not pending:
        print("\nAll agent_eval experiments complete.")
        _write_leaderboard(project, plan, completed)
        return 0

    agent_id, pv, spec = pending[0]
    key = _experiment_key(agent_id, pv, spec)
    agent_spec = get_agent_spec(agent_id)
    print(
        f"\nRunning {done_count + 1}/{total}: agent={agent_id} prompt={pv} "
        f"model={spec.model} ({spec.provider}) | {agent_spec.example_count} examples\n"
    )

    from langsmith import Client

    client = Client()
    try:
        row = run_single_experiment(client, agent_id=agent_id, prompt_version=pv, spec=spec)
    except RateLimitAbort as exc:
        print(f"\n[GUARD] BLOCKED — no traces were created.\n{exc}")
        return 2
    except Exception as exc:
        logger.error("Experiment failed agent=%s prompt=%s model=%s: %s", agent_id, pv, spec.model, exc)
        print(f"\nExperiment FAILED: {exc}")
        return 1

    completed[key] = row
    ckpt["completed"] = completed
    ckpt["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_checkpoint(ckpt)

    new_done = done_count + 1
    print("\n" + "-" * 72)
    print(f"DONE {new_done}/{total}: {agent_id} / {pv} / {spec.model}")
    if row.get("langsmith_url"):
        print(f"View: {row['langsmith_url']}")
    if total - new_done > 0:
        nxt_a, nxt_pv, nxt_spec = pending[1]
        print(f"\nNEXT: {nxt_a} / {nxt_pv} / {nxt_spec.model}")
        print("  python -m evals.agent_eval.run_matrix --step")
    else:
        _write_leaderboard(project, plan, completed)
    print("-" * 72)
    return 0


def run_loop(
    *,
    agent_ids: Optional[List[str]] = None,
    prompts: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    max_steps: Optional[int] = None,
) -> int:
    """Run every pending experiment one-by-one in a single process (checkpointed).

    Identical scope/skip rules as step mode (Gemini + deepseek skipped at
    runtime). Safe to interrupt and resume: each completed experiment is saved
    to the checkpoint immediately, so re-running continues where it left off.
    """
    ensure_langsmith_env()
    project = get_langsmith_project()

    agents = list(agent_ids or list_scope_agents())
    prompt_list = list(prompts or PROMPT_VERSIONS)
    plan = _build_plan(agents, prompt_list, models)
    total = len(plan)

    from langsmith import Client

    client = Client()

    steps_run = 0
    while True:
        ckpt = _load_checkpoint()
        completed: Dict[str, Any] = ckpt.get("completed", {})
        done_count = sum(1 for a, pv, spec in plan if _is_done(completed, _experiment_key(a, pv, spec)))
        pending = [(a, pv, spec) for a, pv, spec in plan if not _is_done(completed, _experiment_key(a, pv, spec))]

        if not pending:
            print(f"\nAll {total} experiments complete.")
            _write_leaderboard(project, plan, completed)
            return 0
        if max_steps is not None and steps_run >= max_steps:
            print(f"\nReached max_steps={max_steps}; {len(pending)} still pending.")
            _write_leaderboard(project, plan, completed)
            return 0

        agent_id, pv, spec = pending[0]
        key = _experiment_key(agent_id, pv, spec)
        try:
            agent_spec = get_agent_spec(agent_id)
            n_examples = agent_spec.example_count
        except Exception:
            n_examples = "?"
        print("=" * 72)
        print(
            f"[{done_count + 1}/{total}] agent={agent_id} prompt={pv} "
            f"model={spec.model} ({spec.provider}) | {n_examples} examples"
        )
        print("=" * 72)

        try:
            row = run_single_experiment(client, agent_id=agent_id, prompt_version=pv, spec=spec)
        except RateLimitAbort as exc:
            print(f"\n[GUARD] BLOCKED — no traces were created. Stopping loop.\n{exc}")
            _write_leaderboard(project, plan, completed)
            return 2
        except Exception as exc:
            logger.error("Experiment failed agent=%s prompt=%s model=%s: %s", agent_id, pv, spec.model, exc)
            print(f"\nExperiment FAILED ({agent_id}/{pv}/{spec.model}): {exc}")
            # Record the failure so the loop advances instead of looping forever.
            row = {
                "agent_id": agent_id,
                "experiment_prefix": _safe_prefix(f"ae-{agent_id}-{pv}-{spec.label}"),
                "prompt_version": pv,
                "provider": spec.provider,
                "model": spec.model,
                "status": "error",
                "error": str(exc)[:500],
            }

        completed[key] = row
        ckpt["completed"] = completed
        ckpt["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_checkpoint(ckpt)
        steps_run += 1

        status = row.get("status", "ok")
        print(f"\nDONE [{done_count + 1}/{total}] {agent_id}/{pv}/{spec.model} -> {status}")
        if row.get("langsmith_url"):
            print(f"View: {row['langsmith_url']}")


def _write_leaderboard(project: str, plan, completed) -> None:
    rows = [
        completed[_experiment_key(a, pv, spec)]
        for a, pv, spec in plan
        if _experiment_key(a, pv, spec) in completed
    ]
    ok_count = sum(1 for e in rows if e.get("ship_recommendation") == "OK")
    by_agent: Dict[str, List[dict]] = {}
    for row in rows:
        by_agent.setdefault(row["agent_id"], []).append(row)

    winners: Dict[str, dict] = {}
    for agent_id, agent_rows in by_agent.items():
        ok_rows = [r for r in agent_rows if r.get("ship_recommendation") == "OK"]
        pool = ok_rows or agent_rows
        best = max(pool, key=lambda r: (r.get("severity_score") or 0, -r.get("elapsed_seconds", 9999)))
        winners[agent_id] = {
            "prompt_version": best.get("prompt_version"),
            "provider": best.get("provider"),
            "model": best.get("model"),
            "ship_recommendation": best.get("ship_recommendation"),
            "severity_score": best.get("severity_score"),
            "experiment_name": best.get("experiment_name"),
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "langsmith_project": project,
        "mode": "stepwise",
        "harness": "agent_eval",
        "note": "intent_classifier uses evals.intent_classifier_eval (unchanged)",
        "experiments": rows,
        "winners_by_agent": winners,
        "summary": {
            "total_experiments": len(rows),
            "ship_ok_count": ok_count,
            "pass_rate": round(ok_count / max(len(rows), 1), 3),
        },
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"leaderboard_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nLeaderboard written to {out}")


def run_matrix(
    *,
    agent_ids: Optional[List[str]] = None,
    prompts: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    dry_run: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    ensure_langsmith_env()
    project = get_langsmith_project()
    agents = list(agent_ids or list_scope_agents())
    prompt_list = list(prompts or PROMPT_VERSIONS)

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "langsmith_project": project,
        "agents": agents,
        "prompt_versions": prompt_list,
        "experiments": [],
        "dry_run": dry_run,
    }

    if dry_run:
        for agent_id in agents:
            active, skipped = _active_models(agent_id)
            active = _filter_active_models(active, models)
            for pv in prompt_list:
                for spec in active:
                    report["experiments"].append(
                        run_single_experiment(
                            None,
                            agent_id=agent_id,
                            prompt_version=pv,
                            spec=spec,
                            dry_run=True,
                            limit=limit,
                            offset=offset,
                        )
                    )
        return report

    from langsmith import Client

    client = Client()
    for agent_id in agents:
        active, _ = _active_models(agent_id)
        active = _filter_active_models(active, models)
        for pv in prompt_list:
            for spec in active:
                logger.info("Running agent=%s prompt=%s model=%s", agent_id, pv, spec.model)
                try:
                    row = run_single_experiment(
                        client, agent_id=agent_id, prompt_version=pv, spec=spec, limit=limit, offset=offset
                    )
                    report["experiments"].append(row)
                except Exception as exc:
                    logger.error("Failed agent=%s prompt=%s: %s", agent_id, pv, exc)
                    report["experiments"].append(
                        {
                            "agent_id": agent_id,
                            "prompt_version": pv,
                            "provider": spec.provider,
                            "model": spec.model,
                            "status": "error",
                            "error": str(exc),
                        }
                    )

    ok_count = sum(1 for e in report["experiments"] if e.get("ship_recommendation") == "OK")
    report["summary"] = {
        "total_experiments": len(report["experiments"]),
        "ship_ok_count": ok_count,
        "pass_rate": round(ok_count / max(len(report["experiments"]), 1), 3),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-agent LangSmith eval matrix (14 agents)")
    parser.add_argument("--agent", action="append", help="Filter agent id(s)")
    parser.add_argument("--prompt", action="append", help="Prompt version(s) v1/v2/v3")
    parser.add_argument("--model", action="append", help="Filter model id(s), e.g. gpt-5-nano")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=None)
    parser.add_argument("--step", action="store_true", help="Run one experiment per invocation")
    parser.add_argument("--all", action="store_true", help="Run all pending experiments one-by-one (checkpointed)")
    parser.add_argument("--max-steps", type=int, default=None, help="With --all: cap experiments this run")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    agents = args.agent or list_scope_agents()
    prompts = args.prompt or list(PROMPT_VERSIONS)
    models = args.model or None

    if args.reset:
        if STEP_CHECKPOINT.exists():
            STEP_CHECKPOINT.unlink()
            print(f"Checkpoint cleared: {STEP_CHECKPOINT}")
        if not (args.step or args.status):
            return 0

    if args.all:
        return run_loop(agent_ids=agents, prompts=prompts, models=models, max_steps=args.max_steps)

    if args.step or args.status:
        return run_stepwise(agent_ids=agents, prompts=prompts, models=models, status_only=args.status)

    report = run_matrix(
        agent_ids=agents,
        prompts=prompts,
        models=models,
        dry_run=args.dry_run,
        limit=args.limit,
        offset=args.offset,
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = (
        Path(args.output)
        if args.output
        else REPORTS_DIR / f"matrix_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
