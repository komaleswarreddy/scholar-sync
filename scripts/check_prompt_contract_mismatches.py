#!/usr/bin/env python3
"""Flag xlsx prompt contracts that disagree with evaluator/dataset (eval_wins)."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.agent_eval.registry import AGENT_EVALUATOR_FILES, XLSX_AGENT_NAME_TO_ID, list_scope_agents

XLSX_PATH = ROOT / "Reference dataset" / "Final Prompt Versions.xlsx"
PROMPT_ROOT = ROOT / "evals" / "agent_eval" / "prompt_versions"
MANIFEST_PATH = ROOT / "evals" / "datasets" / "prompt_tiered" / "manifest.json"

SKIP_AGENTS = frozenset({"Intent Classifier Agent"})


def _load_evaluator_schema(agent_id: str) -> dict:
    path = ROOT / "evals" / "datasets" / "final_Evalutors" / AGENT_EVALUATOR_FILES[agent_id]
    src = path.read_text(encoding="utf-8")
    keys = set()
    for m in re.finditer(r'"([a-z_]+)"\s*:\s*(?:string|bool|number|float|list)', src, re.I):
        keys.add(m.group(1))
    for m in re.finditer(r"REQUIRED_KEYS\s*=\s*\{([^}]+)\}", src):
        keys.update(re.findall(r'"([a-z_]+)"', m.group(1)))
    for m in re.finditer(r"VALID_[A-Z_]+\s*=\s*\{", src):
        pass
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = next(d for d in manifest["datasets"] if d["dataset_id"] == agent_id)
    ds = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
    output_keys = list((ds.get("langsmith") or {}).get("output_keys") or [])
    return {"output_keys": output_keys, "evaluator_hints": sorted(keys)}


def _xlsx_v1_system(agent_name: str) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb["Final Prompt Versions"]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if (row[1] or "").strip() == agent_name:
            return str(row[2] or "")
    return ""


def _keys_in_prompt(text: str) -> set[str]:
    return set(re.findall(r'`"?([a-z_]+)"?`?\s*(?:\(|:|\||MUST)', text, re.I)) | set(
        re.findall(r'Keys \(exactly\):\s*([^\n]+)', text)
    )


def check() -> dict:
    report = {"mismatches": [], "ok": [], "skipped": []}

    report["skipped"].append(
        {
            "agent_id": "intent_classifier",
            "reason": "unchanged — uses evals/intent_classifier_eval with 6-field contract",
        }
    )

    for agent_name, agent_id in XLSX_AGENT_NAME_TO_ID.items():
        if agent_id not in list_scope_agents():
            continue
        schema = _load_evaluator_schema(agent_id)
        output_keys = set(schema["output_keys"])
        sys_path = PROMPT_ROOT / agent_id / "v1_system.txt"
        prompt_text = sys_path.read_text(encoding="utf-8") if sys_path.is_file() else _xlsx_v1_system(agent_name)

        missing_in_prompt = []
        for key in output_keys:
            if key not in prompt_text:
                missing_in_prompt.append(key)

        if missing_in_prompt:
            report["mismatches"].append(
                {
                    "agent_id": agent_id,
                    "eval_wins": True,
                    "action": "keep evaluator+dataset; xlsx prompt may not list all output keys",
                    "dataset_output_keys": sorted(output_keys),
                    "keys_not_obvious_in_xlsx_prompt": missing_in_prompt,
                }
            )
        else:
            report["ok"].append({"agent_id": agent_id})

    out = ROOT / "evals" / "reports" / "agent_matrix" / "contract_check_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> int:
    check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
