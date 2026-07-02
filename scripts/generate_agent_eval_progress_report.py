#!/usr/bin/env python3
"""
Generate per-agent eval progress summary + per-experiment LangSmith links CSV.

Covers completed agents from intent_classifier through the latest agent_eval batch.
Uses read-only LangSmith API calls (no trace quota consumption).
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import os
import requests

from evals.agent_eval.config import dataset_name

REPORTS_DIR = ROOT / "evals" / "reports" / "agent_eval_progress"
KEYS_STORE = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys.json"
KEYS_CACHE = ROOT / "evals" / "reports" / "agent_matrix" / "workspace_keys_cache.json"
AGENT_MODELS = ROOT / "evals" / "agent_eval" / "agent_models.json"
LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"

V1_ONLY_AGENTS = frozenset({"chat_policy_block", "hallucination_guard_retry"})
SKIP_AGENTS = frozenset({"chunk_contextualization", "document_sketch"})

AGENT_ORDER: List[Tuple[int, str, str]] = [
    (1, "intent_classifier", "Intent Classifier"),
    (2, "query_rewriter", "Query Rewriter"),
    (3, "query_decomposer", "Query Decomposer"),
    (4, "scope_narrower", "Scope Narrower"),
    (5, "direct_chat", "Direct Chat"),
    (6, "chat_summarizer", "Chat Summarizer"),
    (7, "chat_policy_block", "Chat Policy Block"),
    (8, "hallucination_guard_retry", "Hallucination Guard Retry"),
    (9, "rag_chat_response_generator", "RAG Chat Response Generator"),
    (10, "studio_system_json", "Studio System JSON"),
    (11, "studio_quiz", "Studio Quiz"),
    (12, "studio_flashcards", "Studio Flashcards"),
    (13, "studio_mind_map", "Studio Mind Map"),
    (14, "studio_slide_deck", "Studio Slide Deck"),
    (15, "studio_fallback_legacy", "Studio Fallback Legacy"),
    (16, "problem_dna_analyzer", "Problem DNA Analyzer"),
    (17, "whole_file_reduce", "Whole File Reduce"),
    (18, "whole_file_map_summarizer", "Whole File Map Summarizer"),
    (19, "explain_from_basics", "Explain From Basics"),
    (20, "show_best_approach", "Show Best Approach"),
    (21, "show_missing_idea", "Show Missing Idea"),
    (22, "ncert_document_sketch", "NCERT Document Sketch"),
]

_TENANT_RE = re.compile(r"/o/([0-9a-f-]+)/")
_COMPARE_RE = re.compile(
    r"https://smith\.langchain\.com/o/[0-9a-f-]+/datasets/[0-9a-f-]+/compare\?selectedSessions=[0-9a-f-]+"
)
_EXP_NAME_RE = re.compile(r"'([^']+)' at:")
_SHIP_RE = re.compile(r"ship_recommendation=\"?([A-Z]+)\"?")


def _all_stored_keys() -> List[str]:
    """Keys from workspace_keys.json only (stable Key A/B/C numbering)."""
    if not KEYS_STORE.is_file():
        return []
    doc = json.loads(KEYS_STORE.read_text(encoding="utf-8"))
    return [str(k).strip() for k in (doc.get("keys") or []) if str(k).strip()]


def _all_keys() -> List[str]:
    keys: List[str] = []
    env_key = (os.environ.get("LANGSMITH_API_KEY") or "").strip()
    if env_key:
        keys.append(env_key)
    for k in _all_stored_keys():
        if k not in keys:
            keys.append(k)
    return keys


def _resolve_tenant(api_key: str) -> Optional[str]:
    try:
        r = requests.get(
            f"{LANGSMITH_ENDPOINT}/api/v1/workspaces",
            headers={"x-api-key": api_key},
            timeout=20,
        )
        if r.ok and r.json():
            return str(r.json()[0]["id"])
    except Exception:
        pass
    return None


def _build_tenant_keys() -> Dict[str, str]:
    cache: Dict[str, str] = {}
    if KEYS_CACHE.is_file():
        try:
            cache = json.loads(KEYS_CACHE.read_text(encoding="utf-8")) or {}
        except Exception:
            cache = {}
    key_to_tenant = {v: k for k, v in cache.items()}
    tenant_keys: Dict[str, str] = {}
    for key in _all_keys():
        tenant = key_to_tenant.get(key) or _resolve_tenant(key)
        if not tenant:
            continue
        tenant_keys[tenant] = key
        cache[tenant] = key
    try:
        KEYS_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass
    return tenant_keys


def _tenant_of(url: str) -> Optional[str]:
    m = _TENANT_RE.search(url or "")
    return m.group(1) if m else None


def _exp_key(agent_id: str, prompt_version: str, model: str) -> str:
    return f"{agent_id}::{prompt_version}::{model}"


def _load_json_completed(path: Path, agent_field: str = "agent_id") -> Dict[str, Dict[str, Any]]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Any]] = {}
    for row in (doc.get("completed") or {}).values():
        agent_id = row.get(agent_field) or "intent_classifier"
        pv = row.get("prompt_version", "")
        model = row.get("model", "")
        if not pv or not model:
            continue
        key = _exp_key(agent_id, pv, model)
        merged = dict(row)
        merged["agent_id"] = agent_id
        if key not in out or merged.get("experiment_name"):
            out[key] = merged
    return out


def _load_leaderboard_experiments() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for fp in sorted(glob.glob(str(ROOT / "evals/reports/agent_matrix/leaderboard_*.json"))):
        doc = json.loads(Path(fp).read_text(encoding="utf-8"))
        for row in doc.get("experiments") or []:
            agent_id = row.get("agent_id")
            pv = row.get("prompt_version")
            model = row.get("model")
            if not agent_id or not pv or not model:
                continue
            key = _exp_key(agent_id, pv, model)
            merged = dict(row)
            if key not in out or merged.get("experiment_name"):
                out[key] = merged
    return out


def _load_full_report_summary() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    pattern = str(ROOT / "evals/reports/agent_matrix_full/full_report_summary_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        return out
    latest = files[-1]
    with open(latest, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("agent_id") or not row.get("prompt_version") or not row.get("model"):
                continue
            key = _exp_key(row["agent_id"], row["prompt_version"], row["model"])
            out[key] = {
                "agent_id": row["agent_id"],
                "prompt_version": row["prompt_version"],
                "model": row["model"],
                "provider": row.get("provider"),
                "experiment_name": row.get("experiment_name"),
                "workspace_tenant": row.get("workspace_tenant"),
                "overall_mean_score": row.get("overall_mean_score"),
                "n_examples": row.get("n_examples"),
            }
    return out


def _parse_log_compare_links() -> Dict[str, str]:
    links: Dict[str, str] = {}
    log_globs = [
        ROOT / "evals/reports/agent_matrix/*.log",
        ROOT / "evals/reports/intent_classifier_langsmith/*.log",
    ]
    for pattern in log_globs:
        for fp in glob.glob(str(pattern)):
            text = Path(fp).read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            for i, line in enumerate(lines):
                m = _EXP_NAME_RE.search(line)
                if not m:
                    continue
                exp_name = m.group(1)
                for j in range(i + 1, min(i + 4, len(lines))):
                    cm = _COMPARE_RE.search(lines[j])
                    if cm:
                        links[exp_name] = cm.group(0)
                        break
    return links


def _expected_prompts(agent_id: str) -> List[str]:
    if agent_id in V1_ONLY_AGENTS:
        return ["v1"]
    return ["v1", "v2", "v3"]


def _expected_models(agent_id: str) -> List[str]:
    if agent_id == "intent_classifier":
        return ["claude-haiku-4-5", "gpt-5-mini", "gpt-5.4-mini"]
    doc = json.loads(AGENT_MODELS.read_text(encoding="utf-8"))
    models = doc.get("agents", {}).get(agent_id, [])
    return [m["model"] for m in models if not m.get("skip_runtime")]


def _merge_experiments() -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    sources = [
        _load_json_completed(ROOT / "evals/reports/agent_matrix/step_checkpoint_pre_3rd_workspace.json"),
        _load_leaderboard_experiments(),
        _load_full_report_summary(),
        _load_json_completed(ROOT / "evals/reports/agent_matrix/step_checkpoint.json"),
    ]
    ic = _load_json_completed(ROOT / "evals/reports/intent_classifier_langsmith/step_checkpoint.json")
    for k, v in ic.items():
        merged[_exp_key("intent_classifier", v["prompt_version"], v["model"])] = v

    for src in sources:
        for key, row in src.items():
            if key in merged:
                merged[key] = {**merged[key], **{k: v for k, v in row.items() if v not in (None, "")}}
            else:
                merged[key] = dict(row)

    # Drop v2/v3 duplicates for v1-only agents
    filtered: Dict[str, Dict[str, Any]] = {}
    for key, row in merged.items():
        agent_id = row.get("agent_id", key.split("::")[0])
        pv = row.get("prompt_version", key.split("::")[1])
        if agent_id in V1_ONLY_AGENTS and pv != "v1":
            continue
        filtered[key] = row
    return filtered


def _key_label_for_tenant(tenant: str, tenant_keys: Dict[str, str]) -> str:
    store_keys = _all_stored_keys()
    api_key = tenant_keys.get(tenant, "")
    if api_key and api_key in store_keys:
        idx = store_keys.index(api_key)
        letter = chr(ord("A") + idx)
        if idx == 6:
            letter_note = "Key G (DEAD/403 — unused)"
        else:
            letter_note = f"Key {letter}"
        return f"{letter_note} — Gmail: FILL MANUALLY (...{api_key[-6:]})"
    if api_key:
        return f"Gmail: FILL MANUALLY (...{api_key[-6:]})"
    return f"Gmail: FILL MANUALLY (tenant {tenant[:8]}...)"


def _resolve_compare_url(
    client,
    tenant: str,
    agent_id: str,
    experiment_name: str,
    log_links: Dict[str, str],
) -> Optional[str]:
    if experiment_name in log_links:
        return log_links[experiment_name]
    try:
        proj = client.read_project(project_name=experiment_name)
        session_id = str(proj.id)
        ds_id = str(getattr(proj, "reference_dataset_id", "") or "")
        if not ds_id:
            ds = client.read_dataset(dataset_name=dataset_name(agent_id))
            ds_id = str(ds.id)
        return (
            f"https://smith.langchain.com/o/{tenant}/datasets/{ds_id}"
            f"/compare?selectedSessions={session_id}"
        )
    except Exception:
        return None


def _resolve_ship_recommendation(client, experiment_name: str) -> Tuple[Optional[str], Optional[float]]:
    try:
        proj = client.read_project(project_name=experiment_name)
        pid = str(proj.id)
        for fb in client.list_feedback(project_id=pid):
            if fb.run_id is not None:
                continue
            comment = str(getattr(fb, "comment", "") or "")
            if "ship_recommendation" not in comment:
                continue
            m = _SHIP_RE.search(comment)
            if m:
                score = getattr(fb, "score", None)
                try:
                    score = float(score) if score is not None else None
                except Exception:
                    score = None
                return m.group(1), score
    except Exception:
        pass
    return None, None


def _resolve_overall_score(client, experiment_name: str) -> Optional[float]:
    try:
        roots = list(client.list_runs(project_name=experiment_name, is_root=True, limit=200))
        if not roots:
            return None
        run_ids = [str(r.id) for r in roots]
        scores: List[float] = []
        for fb in client.list_feedback(run_ids=run_ids):
            if fb.score is not None and fb.key not in ("severity_tier_summary",):
                try:
                    scores.append(float(fb.score))
                except Exception:
                    pass
        if not scores:
            return None
        return round(sum(scores) / len(scores), 4)
    except Exception:
        return None


def generate(dry_run: bool = False) -> Tuple[Path, Path]:
    tenant_keys = _build_tenant_keys()
    tenant_to_key_label = {t: _key_label_for_tenant(t, tenant_keys) for t in tenant_keys}
    log_links = _parse_log_compare_links()
    experiments = _merge_experiments()

    from langsmith import Client

    clients: Dict[str, Any] = {}
    experiment_rows: List[Dict[str, Any]] = []
    total = len(experiments)
    done = 0

    for key in sorted(experiments.keys()):
        done += 1
        row = experiments[key]
        agent_id = row.get("agent_id") or key.split("::")[0]
        exp_name = row.get("experiment_name", "")
        if done % 10 == 0 or done == total:
            print(f"  resolving {done}/{total}: {agent_id} {exp_name[:50]}...")
        if agent_id in SKIP_AGENTS:
            continue
        exp_name = row.get("experiment_name")
        if not exp_name:
            continue
        pv = row.get("prompt_version", "")
        model = row.get("model", "")
        tenant = row.get("workspace_tenant") or _tenant_of(row.get("langsmith_url", ""))
        if not tenant:
            for t, api_key in tenant_keys.items():
                c = clients.get(t) or Client(api_url=LANGSMITH_ENDPOINT, api_key=api_key)
                clients[t] = c
                try:
                    c.read_project(project_name=exp_name)
                    tenant = t
                    break
                except Exception:
                    continue
        if not tenant or tenant not in tenant_keys:
            compare_url = log_links.get(exp_name)
            ship = row.get("ship_recommendation")
            experiment_rows.append(
                {
                    "agent_id": agent_id,
                    "prompt_version": pv,
                    "model": model,
                    "provider": row.get("provider", ""),
                    "experiment_name": exp_name,
                    "workspace_tenant": tenant or "",
                    "gmail_account": tenant_to_key_label.get(tenant, "UNKNOWN — fill manually"),
                    "overall_score": row.get("overall_mean_score"),
                    "ship_recommendation": ship,
                    "compare_url": compare_url or "LINK NOT RESOLVED",
                    "n_examples": row.get("n_examples") or row.get("traces_agent") or "",
                }
            )
            continue

        if tenant not in clients:
            clients[tenant] = Client(api_url=LANGSMITH_ENDPOINT, api_key=tenant_keys[tenant])
        client = clients[tenant]

        compare_url = _resolve_compare_url(client, tenant, agent_id, exp_name, log_links)
        ship, _ = _resolve_ship_recommendation(client, exp_name)
        score = row.get("overall_mean_score")
        if score in (None, ""):
            score = _resolve_overall_score(client, exp_name)

        experiment_rows.append(
            {
                "agent_id": agent_id,
                "prompt_version": pv,
                "model": model,
                "provider": row.get("provider", ""),
                "experiment_name": exp_name,
                "workspace_tenant": tenant,
                "gmail_account": tenant_to_key_label.get(tenant, "UNKNOWN — fill manually"),
                "overall_score": score,
                "ship_recommendation": ship,
                "compare_url": compare_url or "LINK NOT RESOLVED",
                "n_examples": row.get("n_examples") or row.get("traces_agent") or "",
            }
        )

    # Deduplicate by compare_url (keep first canonical experiment_name per agent/pv/model)
    seen_urls: Set[str] = set()
    deduped_experiments: List[Dict[str, Any]] = []
    for er in experiment_rows:
        url = er.get("compare_url", "")
        dedupe_key = (er["agent_id"], er["prompt_version"], er["model"])
        if url and url != "LINK NOT RESOLVED":
            if url in seen_urls:
                continue
            seen_urls.add(url)
        deduped_experiments.append(er)

    by_agent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for er in deduped_experiments:
        by_agent[er["agent_id"]].append(er)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    links_path = REPORTS_DIR / f"agent_eval_experiment_links_{ts}.csv"
    summary_path = REPORTS_DIR / f"agent_eval_summary_{ts}.csv"

    with open(links_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "S.No",
                "Agent ID",
                "Agent Name",
                "Prompt Version",
                "Model",
                "Provider",
                "Experiment Name",
                "Examples",
                "Overall Score",
                "Ship Recommendation",
                "Workspace Tenant",
                "Gmail Account",
                "Gmail Password",
                "LangSmith Compare Link",
            ]
        )
        n = 0
        for sec, agent_id, agent_name in AGENT_ORDER:
            rows = sorted(
                by_agent.get(agent_id, []),
                key=lambda r: (r["prompt_version"], r["model"]),
            )
            for r in rows:
                n += 1
                w.writerow(
                    [
                        n,
                        agent_id,
                        agent_name,
                        r["prompt_version"],
                        r["model"],
                        r.get("provider", ""),
                        r["experiment_name"],
                        r.get("n_examples", ""),
                        r.get("overall_score", ""),
                        r.get("ship_recommendation", ""),
                        r["workspace_tenant"],
                        r["gmail_account"],
                        "",
                        r["compare_url"],
                    ]
                )

    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "S.No",
                "Agent Name",
                "Agent ID",
                "Models Completed",
                "Models Pending",
                "Prompts Completed",
                "Prompts Pending",
                "Total Experiments Run",
                "Experiments Passed (ship=OK)",
                "Experiments Failed/Review",
                "Workspace Tenant(s)",
                "Gmail Account(s)",
                "Gmail Password",
                "LangSmith Compare Links",
            ]
        )
        for sec, agent_id, agent_name in AGENT_ORDER:
            rows = by_agent.get(agent_id, [])
            completed_models = sorted({r["model"] for r in rows})
            completed_prompts = sorted({r["prompt_version"] for r in rows})
            expected_models = _expected_models(agent_id)
            expected_prompts = _expected_prompts(agent_id)
            pending_models = [m for m in expected_models if m not in completed_models]
            pending_prompts = [p for p in expected_prompts if p not in completed_prompts]

            # show_best_approach: gemini-3.1-pro unavailable
            if agent_id == "show_best_approach" and "gemini-3.1-pro" in pending_models:
                pending_models = [
                    m if m != "gemini-3.1-pro" else "gemini-3.1-pro (API 404 — skipped)"
                    for m in pending_models
                ]

            passed = sum(1 for r in rows if r.get("ship_recommendation") == "OK")
            failed_review = sum(
                1
                for r in rows
                if r.get("ship_recommendation") in ("BLOCK", "REVIEW")
                or (r.get("ship_recommendation") and r.get("ship_recommendation") != "OK")
            )
            tenants = sorted({r["workspace_tenant"] for r in rows if r.get("workspace_tenant")})
            gmails = sorted({r["gmail_account"] for r in rows if r.get("gmail_account")})
            links = [r["compare_url"] for r in sorted(rows, key=lambda x: (x["prompt_version"], x["model"])) if r.get("compare_url") and r["compare_url"] != "LINK NOT RESOLVED"]

            models_completed_str = (
                f"{len(completed_models)}/{len(expected_models)} completed"
                f" — {', '.join(completed_models) if completed_models else 'none'}"
            )
            models_pending_str = ", ".join(pending_models) if pending_models else "none (all planned models done)"
            prompts_completed_str = (
                f"{len(completed_prompts)}/{len(expected_prompts)} completed"
                f" — {', '.join(completed_prompts) if completed_prompts else 'none'}"
            )
            prompts_pending_str = ", ".join(pending_prompts) if pending_prompts else "none (all prompts done)"

            w.writerow(
                [
                    sec,
                    agent_name,
                    agent_id,
                    models_completed_str,
                    models_pending_str,
                    prompts_completed_str,
                    prompts_pending_str,
                    len(rows),
                    passed,
                    failed_review,
                    " | ".join(tenants),
                    " | ".join(gmails),
                    "",
                    "\n".join(links),
                ]
            )

    print(f"Wrote {summary_path}")
    print(f"Wrote {links_path}")
    print(f"Total experiments: {len(deduped_experiments)}")
    print(f"Agents with data: {len(by_agent)}")
    unresolved = sum(1 for r in deduped_experiments if r.get("compare_url") == "LINK NOT RESOLVED")
    print(f"Unresolved links: {unresolved}")
    return summary_path, links_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    generate(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
