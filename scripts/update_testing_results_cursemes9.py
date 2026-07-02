#!/usr/bin/env python3
"""Update Reference dataset/testing_Results.csv for cursemes9 agents (rows 17-27)."""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from evals.agent_eval.config import dataset_name
from langsmith import Client

CHECKPOINT = ROOT / "evals/reports/agent_matrix/step_checkpoint.json"
CSV_PATH = ROOT / "Reference dataset/testing_Results.csv"
AGENT_MODELS = json.loads((ROOT / "evals/agent_eval/agent_models.json").read_text())["agents"]

TENANT = "ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7"
GMAIL = "cursemes9@gmail.com"
PASSWORD = "ASDFvbnm1234@"

# All agents run on cursemes9 workspace (4 re-runs + 7 new)
AGENTS = [
    ("explain_from_basics", "Explain From Basics"),
    ("show_best_approach", "Show Best Approach"),
    ("show_missing_idea", "Show Missing Idea"),
    ("ncert_document_sketch", "NCERT Document Sketch"),
    ("help_me_solve_it", "Help Me Solve It"),
    ("problem_solver_followup", "Problem Solver Follow-up"),
    ("tutor_notebook_bootstrap", "Tutor Notebook Bootstrap"),
    ("tutor_follow_up_questions", "Tutor Follow-up Questions"),
    ("source_question_extraction", "Source Question Extraction"),
    ("image_ocr", "Image OCR"),
    ("diagram_label_ocr", "Diagram Label OCR"),
]


def _compare_url(client: Client, agent_id: str, experiment_name: str) -> str | None:
    try:
        proj = client.read_project(project_name=experiment_name)
        session_id = str(proj.id)
        ds_id = str(getattr(proj, "reference_dataset_id", "") or "")
        if not ds_id:
            ds_id = str(client.read_dataset(dataset_name=dataset_name(agent_id)).id)
        return (
            f"https://smith.langchain.com/o/{TENANT}/datasets/{ds_id}"
            f"/compare?selectedSessions={session_id}"
        )
    except Exception:
        return None


def _expected_models(agent_id: str) -> list[str]:
    return [m["model"] for m in AGENT_MODELS.get(agent_id, [])]


def _skip_models(agent_id: str) -> set[str]:
    return {m["model"] for m in AGENT_MODELS.get(agent_id, []) if m.get("skip_runtime")}


def _pending_label(agent_id: str, model: str) -> str:
    if model == "gemini-3.1-pro":
        return "gemini-3.1-pro (Gemini — API 404, skipped)"
    if model in _skip_models(agent_id):
        return f"{model} (Gemini — health-check skipped)"
    return model


def _build_agent_row(client: Client, agent_id: str, name: str, rows: list[dict]) -> list[str]:
    exp_models = _expected_models(agent_id)
    completed_models = sorted({r["model"] for r in rows})
    completed_prompts = sorted({r["prompt_version"] for r in rows})
    exp_prompts = ["v1", "v2", "v3"]

    pending_models = [_pending_label(agent_id, m) for m in exp_models if m not in completed_models]
    pending_prompts = [p for p in exp_prompts if p not in completed_prompts]

    links = []
    for r in sorted(rows, key=lambda x: (x["prompt_version"], x["model"])):
        url = r.get("compare_url") or _compare_url(client, agent_id, r["experiment_name"])
        if url:
            links.append(url)

    return [
        "",
        name,
        agent_id,
        f"{len(completed_models)}/{len(exp_models)} completed — {', '.join(completed_models) if completed_models else 'none'}",
        ", ".join(pending_models) if pending_models else "none (all planned models done)",
        f"{len(completed_prompts)}/{len(exp_prompts)} completed — {', '.join(completed_prompts) if completed_prompts else 'none'}",
        ", ".join(pending_prompts) if pending_prompts else "none (all prompts done)",
        TENANT,
        GMAIL,
        PASSWORD,
        "\n".join(links),
    ]


def main() -> int:
    if not CHECKPOINT.exists():
        print(f"Missing checkpoint: {CHECKPOINT}")
        return 1

    ckpt = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    completed = ckpt.get("completed", {})
    target_ids = {a[0] for a in AGENTS}

    by_agent: dict[str, list[dict]] = defaultdict(list)
    for key, row in completed.items():
        agent_id = row.get("agent_id") or key.split("::")[0]
        if agent_id not in target_ids:
            continue
        if row.get("status") == "error" or not row.get("experiment_name"):
            continue
        by_agent[agent_id].append(row)

    client = Client()
    for agent_id, _ in AGENTS:
        for row in by_agent[agent_id]:
            row["compare_url"] = _compare_url(client, agent_id, row["experiment_name"])

    existing: list[list[str]] = []
    header = [
        "S.No", "Agent Name", "Agent ID", "Models Completed", "Models Pending",
        "Prompts Completed", "Prompts Pending", "Workspace Tenant(s)",
        "Gmail Account(s)", "Gmail Password", "LangSmith Compare Links",
    ]
    if CSV_PATH.exists():
        reader = csv.reader(open(CSV_PATH, encoding="utf-8"))
        header = next(reader)
        aid_idx = header.index("Agent ID")
        for row in reader:
            if len(row) > aid_idx and row[aid_idx] in target_ids:
                continue
            existing.append(row)

    new_rows = [_build_agent_row(client, aid, name, by_agent[aid]) for aid, name in AGENTS]
    all_rows = existing + new_rows
    for i, row in enumerate(all_rows, 1):
        row[0] = str(i)

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(all_rows)

    for aid, name in AGENTS:
        n = len(by_agent[aid])
        print(f"{name}: {n} experiments, {len([u for u in by_agent[aid] if u.get('compare_url')])} links")
    print(f"Wrote {CSV_PATH} ({len(all_rows)} agent rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
