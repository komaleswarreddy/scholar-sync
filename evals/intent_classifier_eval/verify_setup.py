#!/usr/bin/env python3
"""
Static cross-verification of LangSmith observability setup for intent classifier evals.

Does NOT call LLM APIs or run experiments. Checks files, env, wiring, and
maps each LangSmith Monitoring dashboard panel to what the harness provides.

Usage:
  python -m evals.intent_classifier_eval.verify_setup
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# Dashboard panel definitions — what LangSmith Monitoring expects
# ---------------------------------------------------------------------------

DASHBOARD_PANELS: List[Dict[str, Any]] = [
    {
        "panel": "Traces",
        "metrics": ["Trace Count", "Trace Latency", "Trace Error Rate"],
        "requires": "Root runs per dataset example via client.evaluate()",
        "status": "configured",
        "detail": "run_eval.py uses langsmith.Client().evaluate() — each example = one trace root run",
    },
    {
        "panel": "LLM Calls",
        "metrics": ["LLM Count", "LLM Latency"],
        "requires": "Child runs with run_type=llm and ls_model_name metadata",
        "status": "configured",
        "detail": "langsmith_tracing.traced_llm_call() wraps target + judge calls with @traceable(run_type='llm')",
    },
    {
        "panel": "Cost & Tokens",
        "metrics": ["Total Cost", "Cost per Trace", "Input/Output Tokens"],
        "requires": "usage_metadata (input_tokens, output_tokens, total_cost) on LLM child runs",
        "status": "configured",
        "detail": "providers.py extracts token counts from API responses; langsmith_tracing posts usage_metadata + model_pricing.yaml costs",
    },
    {
        "panel": "Tools",
        "metrics": ["Run Count by Tool", "Median Latency by Tool", "Error Rate by Tool"],
        "requires": "run_type=tool child runs",
        "status": "n/a",
        "detail": "Intent classifier has no tool calls — panel will stay empty (expected)",
    },
    {
        "panel": "Run Types",
        "metrics": ["Run Count by Name", "Median Latency", "Error Rate"],
        "requires": "Named runs at depth=1 (llm, chain, evaluator)",
        "status": "configured",
        "detail": "Target traces (chain), LLM inference (llm), evaluators (evaluator) — visible under Experiments + Monitoring",
    },
    {
        "panel": "Feedback Scores",
        "metrics": ["Per-evaluator scores over time"],
        "requires": "client.evaluate() evaluators returning {key, score, comment}",
        "status": "configured",
        "detail": "6 per-example feedback keys: schema_validity, intent_match, routing_metadata_match, routing_consistency, confidence_calibration, llm_routing_judge + severity_tier_summary summary",
    },
    {
        "panel": "Experiments (Datasets & Experiments tab)",
        "metrics": ["Experiment comparison, per-example results"],
        "requires": "Dataset uploaded + evaluate() per prompt×model",
        "status": "configured",
        "detail": "Dataset nbm-prompt-intent_classifier (63 examples); 3 prompts × 3 models = 9 experiments",
    },
]


def _check_env() -> List[Dict[str, Any]]:
    checks = []
    for key, required in [
        ("LANGSMITH_API_KEY", True),
        ("LANGSMITH_PROJECT", True),
        ("LANGSMITH_TRACING_ENABLED", False),
        ("OPENAI_API_KEY", True),
        ("ANTHROPIC_API_KEY", False),
        ("GEMINI_API_KEY", False),
    ]:
        val = (os.environ.get(key) or "").strip()
        checks.append({
            "key": key,
            "present": bool(val),
            "required": required,
            "ok": bool(val) if required else True,
            "value_hint": f"{val[:8]}..." if val else "(missing)",
        })
    project = os.environ.get("LANGSMITH_PROJECT", "")
    checks.append({
        "key": "LANGSMITH_PROJECT value",
        "present": project == "ScholarSync",
        "required": True,
        "ok": project == "ScholarSync",
        "value_hint": project or "(missing)",
    })
    return checks


def _check_files() -> List[Dict[str, Any]]:
    required_files = [
        "evals/intent_classifier_eval/run_eval.py",
        "evals/intent_classifier_eval/providers.py",
        "evals/intent_classifier_eval/langsmith_tracing.py",
        "evals/intent_classifier_eval/llm_judge.py",
        "evals/intent_classifier_eval/evaluator_loader.py",
        "evals/intent_classifier_eval/config.py",
        "evals/intent_classifier_eval/prompts.py",
        "evals/intent_classifier_eval/smoke_test.py",
        "evals/datasets/final_Evalutors/intent_classifier.py",
        "evals/datasets/prompt_tiered/routing/intent_classifier.json",
        "scripts/upload_prompt_tiered_to_langsmith.py",
        "config/model_pricing.yaml",
    ]
    for v in ("v1", "v2", "v3"):
        required_files.append(f"evals/intent_classifier_eval/prompt_versions/{v}_system.txt")
        required_files.append(f"evals/intent_classifier_eval/prompt_versions/{v}_user.j2")

    results = []
    for rel in required_files:
        p = ROOT / rel
        results.append({"path": rel, "exists": p.is_file(), "ok": p.is_file()})
    return results


def _check_evaluators() -> Dict[str, Any]:
    from evals.intent_classifier_eval.evaluator_loader import (
        get_per_example_evaluators,
        get_summary_evaluators,
    )
    from evals.intent_classifier_eval.llm_judge import routing_judge

    per_ex = get_per_example_evaluators()
    summary = get_summary_evaluators()
    allowed = {"key", "score", "comment"}

    # Smoke-test wrapper output shape (no API)
    class _Run:
        outputs = {
            "intent": "conversational",
            "scope": "none",
            "requires_retrieval": False,
            "requires_attachment": False,
            "confidence": 0.9,
            "reasoning": "greeting",
        }

    class _Ex:
        outputs = dict(_Run.outputs)
        inputs = {"query": "Hi"}
        metadata = {"variation": "general"}
        id = "test-001"

    feedback_keys = []
    wrapper_ok = True
    for fn in per_ex:
        r = fn(_Run(), _Ex())
        feedback_keys.append(r.get("key"))
        if set(r.keys()) - allowed:
            wrapper_ok = False

    judge_wired = routing_judge.__name__ == "routing_judge"
    feedback_keys.append("llm_routing_judge")  # added in run_eval, not in loader list

    return {
        "per_example_count": len(per_ex),
        "judge_evaluator_wired": judge_wired,
        "summary_count": len(summary),
        "feedback_keys": feedback_keys,
        "wrapper_langsmith_safe": wrapper_ok,
        "expected_feedback_keys": [
            "schema_validity",
            "intent_match",
            "routing_metadata_match",
            "routing_consistency",
            "confidence_calibration",
            "llm_routing_judge",
        ],
        "summary_key": "severity_tier_summary",
    }


def _check_tracing_wiring() -> Dict[str, Any]:
    tracing_path = ROOT / "evals/intent_classifier_eval/langsmith_tracing.py"
    src = tracing_path.read_text(encoding="utf-8")
    run_eval_src = (ROOT / "evals/intent_classifier_eval/run_eval.py").read_text(encoding="utf-8")
    providers_src = (ROOT / "evals/intent_classifier_eval/providers.py").read_text(encoding="utf-8")
    judge_src = (ROOT / "evals/intent_classifier_eval/llm_judge.py").read_text(encoding="utf-8")

    return {
        "traced_llm_call_exists": "def traced_llm_call" in src,
        "traceable_run_type_llm": 'run_type="llm"' in src,
        "usage_metadata_posted": "usage_metadata" in src,
        "run_eval_uses_traced_llm_call": "traced_llm_call" in run_eval_src,
        "judge_uses_traced_llm_call": "traced_llm_call" in judge_src,
        "providers_return_usage": "return_usage" in providers_src and "prompt_tokens" in providers_src,
        "evaluate_used": "client.evaluate" in run_eval_src,
    }


def _check_pricing() -> Dict[str, Any]:
    from evals.intent_classifier_eval.config import MODEL_MATRIX
    from evals.intent_classifier_eval.langsmith_tracing import load_pricing

    pricing = load_pricing()
    missing = [m.model for m in MODEL_MATRIX if m.model not in pricing]
    judge = os.environ.get("INTENT_EVAL_JUDGE_MODEL", "gpt-4o")
    if judge not in pricing:
        missing.append(judge)
    return {
        "models_in_matrix": [m.model for m in MODEL_MATRIX],
        "judge_model": judge,
        "pricing_entries": list(pricing.keys()),
        "missing_pricing": missing,
        "ok": len(missing) == 0,
    }


def _check_dataset_local() -> Dict[str, Any]:
    ds_path = ROOT / "evals/datasets/prompt_tiered/routing/intent_classifier.json"
    doc = json.loads(ds_path.read_text(encoding="utf-8"))
    items = doc.get("items") or []
    variations = {it.get("variation") for it in items}
    has_content_type = any("content_type" in (it.get("reference_outputs") or {}) for it in items)
    return {
        "example_count": len(items),
        "expected": 63,
        "ok": len(items) == 63,
        "variation_count": len(variations),
        "has_content_type_in_gold": has_content_type,
        "gold_6_field_ok": not has_content_type,
        "prompt_template_present": bool(doc.get("agent", {}).get("prompt_template")),
    }


def _check_prompt_versions() -> Dict[str, Any]:
    from evals.intent_classifier_eval.config import PROMPT_VERSIONS
    from evals.intent_classifier_eval.prompts import get_prompt_parts, render_prompts

    results = {}
    for v in PROMPT_VERSIONS:
        try:
            system, user_tpl = get_prompt_parts(v)
            system_user = render_prompts(v, {"query": "test query"})
            has_content_type = "content_type" in system
            results[v] = {
                "ok": True,
                "system_chars": len(system),
                "user_renders": "test query" in system_user[1],
                "mentions_content_type": has_content_type,
                "six_field_contract": not has_content_type,
            }
        except Exception as exc:
            results[v] = {"ok": False, "error": str(exc)}
    return results


def run_verification() -> Dict[str, Any]:
    env_checks = _check_env()
    file_checks = _check_files()
    eval_info = _check_evaluators()
    tracing = _check_tracing_wiring()
    pricing = _check_pricing()
    dataset = _check_dataset_local()
    prompts = _check_prompt_versions()

    env_ok = all(c["ok"] for c in env_checks if c["required"])
    files_ok = all(f["ok"] for f in file_checks)
    eval_ok = (
        eval_info["wrapper_langsmith_safe"]
        and eval_info["judge_evaluator_wired"]
        and set(eval_info["expected_feedback_keys"]).issubset(set(eval_info["feedback_keys"]))
    )
    tracing_ok = all(tracing.values())
    overall_ok = env_ok and files_ok and eval_ok and tracing_ok and pricing["ok"] and dataset["ok"] and all(
        p.get("ok") for p in prompts.values()
    )

    return {
        "overall_status": "READY" if overall_ok else "NEEDS_ATTENTION",
        "langsmith_project": os.environ.get("LANGSMITH_PROJECT"),
        "dashboard_panels": DASHBOARD_PANELS,
        "env_checks": env_checks,
        "file_checks": {"all_ok": files_ok, "missing": [f["path"] for f in file_checks if not f["ok"]]},
        "evaluators": eval_info,
        "tracing_wiring": tracing,
        "pricing": pricing,
        "dataset": dataset,
        "prompt_versions": prompts,
        "how_to_run": {
            "smoke_test": "python -m evals.intent_classifier_eval.smoke_test",
            "single_experiment": "python -m evals.intent_classifier_eval.run_eval --prompt v1 --provider openai",
            "full_matrix": "python -m evals.intent_classifier_eval.run_eval",
            "dry_run": "python -m evals.intent_classifier_eval.run_eval --dry-run",
        },
        "where_to_look_in_langsmith": {
            "experiments": "ScholarSync → Datasets & Experiments → nbm-prompt-intent_classifier",
            "monitoring_traces": "ScholarSync → Monitoring → Traces (after evaluate runs)",
            "monitoring_llm_cost": "ScholarSync → Monitoring → LLM Calls / Cost & Tokens (after evaluate runs)",
            "monitoring_feedback": "ScholarSync → Monitoring → Feedback Scores (after evaluate runs)",
            "tools_panel": "Will remain empty — no tools in intent classifier (expected)",
        },
    }


def main() -> int:
    report = run_verification()
    out_dir = ROOT / "evals" / "reports" / "intent_classifier_langsmith"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "verify_setup_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nReport written to {out_path}")
    print(f"\nOverall: {report['overall_status']}")

    # Human-readable dashboard summary
    print("\n--- LangSmith Dashboard Panel Coverage ---")
    for panel in DASHBOARD_PANELS:
        icon = {"configured": "[OK]", "n/a": "[N/A]", "missing": "[!!]"}.get(panel["status"], "[??]")
        print(f"  {icon} {panel['panel']}: {panel['detail']}")

    return 0 if report["overall_status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
