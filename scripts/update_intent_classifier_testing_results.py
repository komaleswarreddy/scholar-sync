#!/usr/bin/env python3
"""
Validate intent_classifier LangSmith experiments and update testing_Results.csv row 1.

Sources (verify-only, no new traces):
  - pscmrmindssprint2k25: gpt-5.4-mini + claude-haiku-4-5 (v1/v2/v3)
  - scombinator26: gpt-5-mini (v1/v2/v3)
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from langsmith import Client

from evals.intent_classifier_eval.config import MODEL_MATRIX, PROMPT_VERSIONS

CSV_PATH = ROOT / "Reference dataset" / "testing_Results.csv"
PASSWORD = "asdfvbnm1234"

# gpt-5.4-mini + haiku live on pscm; gpt-5-mini on scombinator26 (63/63 each).
WORKSPACE_SOURCES: list[dict[str, object]] = [
    {
        "switch": "pscmrmindssprint2k25",
        "tenant": "15d476d5-df92-4760-96b8-52f9130946bf",
        "gmail": "pscmrmindssprint2k25@gmail.com",
        "dataset_id": "295b86be-1402-43ff-939d-538344ae7905",
        "models": {"gpt-5.4-mini", "claude-haiku-4-5"},
    },
    {
        "switch": "scombinator26",
        "tenant": "47ca8a69-43eb-4f05-812b-c7778fe6987d",
        "gmail": "scombinator26@gmail.com",
        "dataset_id": "25a26198-362b-4f9c-a2c9-727e3e1a4620",
        "models": {"gpt-5-mini"},
    },
]

PRIMARY_TENANT = WORKSPACE_SOURCES[0]["tenant"]
PRIMARY_DATASET = WORKSPACE_SOURCES[0]["dataset_id"]


def _switch_workspace(name: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "switch_workspace.py"), name],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
    )
    load_dotenv(ROOT / ".env", override=True)


def _parse_ic_project_name(name: str) -> dict[str, str] | None:
    if not name.startswith("ic-"):
        return None
    rest = name[3:]
    for pv in PROMPT_VERSIONS:
        pv_prefix = f"{pv}-"
        if not rest.startswith(pv_prefix):
            continue
        tail = rest[len(pv_prefix) :]
        for spec in sorted(MODEL_MATRIX, key=lambda s: len(s.label), reverse=True):
            candidates = (
                spec.label,
                spec.model,
                spec.model.replace(".", "-"),
                f"{spec.provider}-{spec.model}".replace(".", "-"),
            )
            for label in candidates:
                label_prefix = f"{label}-"
                if tail.lower().startswith(label_prefix.lower()):
                    return {
                        "experiment_name": name,
                        "prompt_version": pv,
                        "provider": spec.provider,
                        "model": spec.model,
                    }
    return None


def _output_fill_for_project(client: Client, project_id: str) -> tuple[int, int]:
    runs = list(client.list_runs(project_id=project_id, is_root=True, limit=100))
    filled = sum(
        1 for r in runs if isinstance(r.outputs, dict) and bool(r.outputs.keys())
    )
    return filled, len(runs)


def _compare_url(tenant: str, dataset_id: str, session_id: str) -> str:
    return (
        f"https://smith.langchain.com/o/{tenant}/datasets/{dataset_id}"
        f"/compare?selectedSessions={session_id}"
    )


def _is_full_dataset_run(total: int, min_examples: int = 60) -> bool:
    return total >= min_examples


def _discover_valid_from_source(source: dict[str, object]) -> list[tuple[str, dict, int]]:
    _switch_workspace(str(source["switch"]))
    client = Client()
    tenant = str(source["tenant"])
    dataset_id = str(source["dataset_id"])
    allowed_models: set[str] = set(source["models"])  # type: ignore[arg-type]

    valid: list[tuple[str, dict, int]] = []
    try:
        projects = list(client.list_projects(reference_dataset_id=dataset_id, limit=100))
    except Exception as exc:
        print(f"  WARN list_projects failed on {source['switch']}: {exc}")
        return valid

    print(f"Scanning {len(projects)} projects on {source['switch']} ({tenant})...")
    for proj in projects:
        name = str(getattr(proj, "name", "") or "")
        meta = _parse_ic_project_name(name)
        if not meta or meta["model"] not in allowed_models:
            continue
        session_id = str(proj.id)
        try:
            filled, total = _output_fill_for_project(client, session_id)
        except Exception as exc:
            print(f"  SKIP {name}: {exc}")
            continue
        if total == 0 or filled < total:
            print(f"  DROP {meta['prompt_version']}/{meta['model']}: {filled}/{total} outputs")
            continue
        if not _is_full_dataset_run(total):
            print(f"  DROP {meta['prompt_version']}/{meta['model']}: partial {total} examples")
            continue
        url = _compare_url(tenant, dataset_id, session_id)
        print(f"  OK   {meta['prompt_version']}/{meta['model']}: {filled}/{total} -> {name}")
        valid.append((url, meta, total))
    return valid


def _format_links(urls: list[str]) -> str:
    return "\n\n".join(u.strip() for u in urls if u and u.strip())


def main() -> int:
    best: dict[tuple[str, str], tuple[str, dict, int]] = {}
    for source in WORKSPACE_SOURCES:
        for url, meta, total in _discover_valid_from_source(source):
            key = (meta["prompt_version"], meta["model"])
            if key not in best or total > best[key][2]:
                best[key] = (url, meta, total)

    model_order = {m.model: i for i, m in enumerate(MODEL_MATRIX)}
    prompt_order = {p: i for i, p in enumerate(PROMPT_VERSIONS)}
    valid = sorted(
        best.values(),
        key=lambda x: (
            model_order.get(x[1]["model"], 99),
            prompt_order.get(x[1]["prompt_version"], 99),
        ),
    )

    exp_models = [m.model for m in MODEL_MATRIX]
    exp_prompts = list(PROMPT_VERSIONS)
    completed_models = sorted({m["model"] for _, m, _ in valid})
    completed_prompts = sorted({m["prompt_version"] for _, m, _ in valid})
    pending_models = [m for m in exp_models if m not in completed_models]
    pending_prompts = [p for p in exp_prompts if p not in completed_prompts]

    tenants = "; ".join(str(s["tenant"]) for s in WORKSPACE_SOURCES)
    gmails = "; ".join(str(s["gmail"]) for s in WORKSPACE_SOURCES)
    links_cell = _format_links([u for u, _, _ in valid])

    notes = (
        "9/9 complete — gpt-5.4-mini + claude-haiku-4-5 on pscmrmindssprint2k25; "
        "gpt-5-mini on scombinator26 (63/63 outputs each)."
        if not pending_models and not pending_prompts
        else " | ".join(f"Pending model: {m}" for m in pending_models)
        + (f" | Pending prompts: {', '.join(pending_prompts)}" if pending_prompts else "")
    )

    new_row = [
        "1",
        "Intent Classifier",
        "intent_classifier",
        f"{len(completed_models)}/{len(exp_models)} completed — {', '.join(completed_models) if completed_models else 'none'}",
        ", ".join(pending_models) if pending_models else "none (all planned models done)",
        f"{len(completed_prompts)}/{len(exp_prompts)} completed — {', '.join(completed_prompts) if completed_prompts else 'none'}",
        ", ".join(pending_prompts) if pending_prompts else "none (all prompts done)",
        tenants,
        gmails,
        PASSWORD,
        links_cell,
        PRIMARY_DATASET,
        PRIMARY_TENANT,
        notes,
    ]

    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    for col in ("LangSmith Dataset ID", "Primary Workspace Tenant", "Run Issues / Notes"):
        if col not in header:
            header.append(col)

    out: list[list[str]] = [header]
    replaced = False
    for row in rows[1:]:
        if len(row) > 2 and row[2].strip() == "intent_classifier":
            while len(new_row) < len(header):
                new_row.append("")
            out.append(new_row[: len(header)])
            replaced = True
        else:
            while len(row) < len(header):
                row.append("")
            out.append(row)
    if not replaced:
        while len(new_row) < len(header):
            new_row.append("")
        out.append(new_row[: len(header)])

    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(out)

    print(f"\nWrote intent_classifier row: {len(valid)}/9 valid links")
    print(f"Updated {CSV_PATH}")
    if pending_models or pending_prompts:
        print(f"Still pending models: {pending_models or 'none'}")
        print(f"Still pending prompts: {pending_prompts or 'none'}")
    return 0 if len(valid) == 9 else 1


if __name__ == "__main__":
    raise SystemExit(main())
