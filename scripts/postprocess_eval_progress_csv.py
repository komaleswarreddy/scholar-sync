#!/usr/bin/env python3
"""Post-process agent eval progress CSVs for human-readable formatting."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_DIR = ROOT / "evals" / "reports" / "agent_eval_progress"
LINKS_PATH = PROGRESS_DIR / "agent_eval_experiment_links_20260630T134011Z.csv"
SUMMARY_PATH = PROGRESS_DIR / "agent_eval_summary_20260630T134011Z.csv"
KEY_REF_PATH = PROGRESS_DIR / "langsmith_key_gmail_reference.csv"

V1_ONLY = frozenset({"chat_policy_block", "hallucination_guard_retry"})
AGENT_MODELS = json.loads((ROOT / "evals/agent_eval/agent_models.json").read_text())["agents"]
STORE_KEYS = json.loads((ROOT / "evals/reports/agent_matrix/workspace_keys.json").read_text())["keys"]
TENANT_CACHE = json.loads((ROOT / "evals/reports/agent_matrix/workspace_keys_cache.json").read_text())

# Score-based ship-readiness threshold (overall mean evaluator score, 0..1).
PASS_THRESHOLD = 0.70

MATRIX_SUMMARY = ROOT / "evals/reports/agent_matrix_full/full_report_summary_20260630T034045Z.csv"
INTENT_SUMMARY = ROOT / "evals/reports/intent_classifier_langsmith/full_report_summary_20260629T112838Z.csv"
NEW_AGENT_SCORES = PROGRESS_DIR / "new_agent_score_cache.json"


def _build_score_map() -> dict[str, float]:
    """Map experiment_name -> overall mean evaluator score across all sources."""
    scores: dict[str, float] = {}
    # 15 matrix agents.
    for row in csv.DictReader(open(MATRIX_SUMMARY, encoding="utf-8-sig")):
        name = row.get("experiment_name")
        raw = row.get("overall_mean_score")
        if name and raw not in (None, ""):
            try:
                scores[name] = round(float(raw), 4)
            except ValueError:
                pass
    # Intent classifier (deterministic score).
    for row in csv.DictReader(open(INTENT_SUMMARY, encoding="utf-8-sig")):
        name = row.get("experiment_name")
        raw = row.get("overall_mean_deterministic_score")
        if name and raw not in (None, ""):
            try:
                scores[name] = round(float(raw), 4)
            except ValueError:
                pass
    # 7 new agents (resolved via LangSmith API).
    if NEW_AGENT_SCORES.exists():
        for name, val in json.loads(NEW_AGENT_SCORES.read_text()).items():
            if val is not None:
                scores[name] = round(float(val), 4)
    return scores


SCORE_MAP = _build_score_map()

AGENT_ORDER = [
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


def expected_models(agent_id: str) -> list[str]:
    """All configured (planned) models, including ones flagged skip_runtime."""
    if agent_id == "intent_classifier":
        return ["claude-haiku-4-5", "gpt-5-mini", "gpt-5.4-mini"]
    return [m["model"] for m in AGENT_MODELS.get(agent_id, [])]


def skip_runtime_models(agent_id: str) -> set[str]:
    return {m["model"] for m in AGENT_MODELS.get(agent_id, []) if m.get("skip_runtime")}


def expected_prompts(agent_id: str) -> list[str]:
    return ["v1"] if agent_id in V1_ONLY else ["v1", "v2", "v3"]


def gmail_label(tenant: str) -> str:
    key = TENANT_CACHE.get(tenant, "")
    if key in STORE_KEYS:
        idx = STORE_KEYS.index(key)
        letter = chr(ord("A") + idx)
        if idx == 6:
            return f"Key G (DEAD/403) — Gmail: FILL MANUALLY (...{key[-6:]})"
        return f"Key {letter} — Gmail: FILL MANUALLY (...{key[-6:]})"
    return "Gmail: FILL MANUALLY"


def main() -> None:
    rows = list(csv.DictReader(open(LINKS_PATH, encoding="utf-8")))
    by_agent: dict[str, list] = defaultdict(list)
    for row in rows:
        by_agent[row["Agent ID"]].append(row)

    fieldnames = list(rows[0].keys())
    with open(LINKS_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            row["Gmail Account"] = gmail_label(row["Workspace Tenant"])
            score = SCORE_MAP.get(row.get("Experiment Name", ""))
            if score is not None:
                row["Overall Score"] = score
            w.writerow(row)

    with open(SUMMARY_PATH, "w", encoding="utf-8", newline="") as f:
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
                "Avg Overall Score",
                f"Experiments Passed (score>={PASS_THRESHOLD:.2f})",
                f"Experiments Below Threshold (score<{PASS_THRESHOLD:.2f})",
                "Workspace Tenant(s)",
                "Gmail Account(s)",
                "Gmail Password",
                "LangSmith Compare Links",
            ]
        )
        for sec, agent_id, name in AGENT_ORDER:
            agent_rows = sorted(
                by_agent.get(agent_id, []),
                key=lambda x: (x["Prompt Version"], x["Model"]),
            )
            completed_models = sorted({r["Model"] for r in agent_rows})
            completed_prompts = sorted({r["Prompt Version"] for r in agent_rows})
            exp_models = expected_models(agent_id)
            exp_prompts = expected_prompts(agent_id)
            skipped = skip_runtime_models(agent_id)
            pending_models = []
            for m in exp_models:
                if m in completed_models:
                    continue
                if m == "gemini-3.1-pro":
                    pending_models.append("gemini-3.1-pro (Gemini — API 404, skipped)")
                elif m in skipped:
                    pending_models.append(f"{m} (Gemini — health-check skipped)")
                else:
                    pending_models.append(m)
            pending_prompts = [p for p in exp_prompts if p not in completed_prompts]
            exp_scores = [
                SCORE_MAP[r["Experiment Name"]]
                for r in agent_rows
                if r.get("Experiment Name") in SCORE_MAP
            ]
            avg_score = round(sum(exp_scores) / len(exp_scores), 4) if exp_scores else None
            passed = sum(1 for s in exp_scores if s >= PASS_THRESHOLD)
            below = sum(1 for s in exp_scores if s < PASS_THRESHOLD)
            missing = len(agent_rows) - len(exp_scores)
            avg_str = f"{avg_score:.4f}" if avg_score is not None else "n/a"
            if missing:
                avg_str += f" ({missing} unscored)"
            tenants = sorted({r["Workspace Tenant"] for r in agent_rows if r.get("Workspace Tenant")})
            gmails = sorted({gmail_label(t) for t in tenants})
            links = [r["LangSmith Compare Link"] for r in agent_rows if r.get("LangSmith Compare Link")]
            w.writerow(
                [
                    sec,
                    name,
                    agent_id,
                    f"{len(completed_models)}/{len(exp_models)} completed — {', '.join(completed_models) if completed_models else 'none'}",
                    ", ".join(pending_models) if pending_models else "none (all planned models done)",
                    f"{len(completed_prompts)}/{len(exp_prompts)} completed — {', '.join(completed_prompts) if completed_prompts else 'none'}",
                    ", ".join(pending_prompts) if pending_prompts else "none (all prompts done)",
                    len(agent_rows),
                    avg_str,
                    passed,
                    below,
                    " | ".join(tenants),
                    " | ".join(gmails),
                    "",
                    "\n".join(links),
                ]
            )

    import requests

    with open(KEY_REF_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["Key Label", "API Key Suffix", "Workspace Tenant", "Status", "Gmail Account", "Gmail Password"]
        )
        for i, key in enumerate(STORE_KEYS):
            letter = chr(ord("A") + i)
            try:
                resp = requests.get(
                    "https://api.smith.langchain.com/api/v1/workspaces",
                    headers={"x-api-key": key},
                    timeout=15,
                )
                tenant = resp.json()[0]["id"] if resp.ok and resp.json() else ""
                status = "ACTIVE" if resp.ok else f"FAILED {resp.status_code}"
            except Exception:
                tenant, status = "", "ERROR"
            w.writerow([f"Key {letter}", f"...{key[-6:]}", tenant, status, "", ""])

    print(f"Updated {SUMMARY_PATH}")
    print(f"Updated {LINKS_PATH}")
    print(f"Wrote {KEY_REF_PATH}")


if __name__ == "__main__":
    main()
