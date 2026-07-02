#!/usr/bin/env python3
"""Extract Version A/B/C prompts from Final Prompt Versions.xlsx -> agent_eval/prompt_versions/."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.agent_eval.registry import XLSX_AGENT_NAME_TO_ID, list_scope_agents

XLSX_PATH = ROOT / "Reference dataset" / "Final Prompt Versions.xlsx"
OUT_ROOT = ROOT / "evals" / "agent_eval" / "prompt_versions"
MANIFEST_PATH = ROOT / "evals" / "datasets" / "prompt_tiered" / "manifest.json"

# intent_classifier uses evals/intent_classifier_eval/prompt_versions — never overwrite.
SKIP_AGENTS = frozenset({"Intent Classifier Agent"})


def _normalize_system(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip()
    if t.upper().startswith("SYSTEM:"):
        t = t[7:].lstrip("\n").strip()
    if t.upper().startswith("SYSTEM\n"):
        t = t[6:].lstrip("\n").strip()
    return t


def _load_input_keys(agent_id: str) -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = next(d for d in manifest["datasets"] if d["dataset_id"] == agent_id)
    ds = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
    return list((ds.get("langsmith") or {}).get("input_keys") or [])


def _build_user_j2(agent_id: str, input_keys: list[str]) -> str:
    """Generic user template from dataset input_keys."""
    lines = ["{# Auto-generated from dataset langsmith.input_keys #}", ""]
    label_map = {
        "query": "Current user message",
        "message": "User message",
        "user_message": "User message",
        "context": "Context",
        "user_request": "User request",
        "draft_answer": "Draft answer",
        "transcript_section": "Conversation transcript",
        "custom_instructions": "Custom instructions",
    }
    for key in input_keys:
        label = label_map.get(key, key.replace("_", " ").title())
        lines.append(f"## {label}")
        lines.append(f"{{{{ {key} }}}}")
        lines.append("")
    lines.append("## Task")
    lines.append("Follow the system instructions and produce the required output format.")
    return "\n".join(lines) + "\n"


def extract(*, force: bool = False) -> dict:
    try:
        import openpyxl
    except ImportError as exc:
        raise SystemExit("openpyxl required: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb["Final Prompt Versions"]
    seen: set[str] = set()
    report = {"written": [], "skipped": [], "flags": []}

    for row in ws.iter_rows(min_row=2, values_only=True):
        agent_name = (row[1] or "").strip() if len(row) > 1 else ""
        if not agent_name or agent_name in SKIP_AGENTS:
            if agent_name in SKIP_AGENTS:
                report["skipped"].append({"agent": agent_name, "reason": "intent_classifier_eval unchanged"})
            continue
        if agent_name in seen:
            report["skipped"].append({"agent": agent_name, "reason": "duplicate xlsx row"})
            continue
        seen.add(agent_name)

        agent_id = XLSX_AGENT_NAME_TO_ID.get(agent_name)
        if not agent_id or agent_id not in list_scope_agents():
            report["skipped"].append({"agent": agent_name, "reason": "not in agent_eval scope"})
            continue

        versions = {
            "v1": _normalize_system(row[2] if len(row) > 2 else ""),
            "v2": _normalize_system(row[3] if len(row) > 3 else ""),
            "v3": _normalize_system(row[4] if len(row) > 4 else ""),
        }
        if not any(versions.values()):
            report["flags"].append({"agent_id": agent_id, "issue": "empty prompt versions in xlsx"})
            continue

        agent_dir = OUT_ROOT / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        input_keys = _load_input_keys(agent_id)
        user_j2 = _build_user_j2(agent_id, input_keys)
        if not input_keys:
            report["flags"].append({"agent_id": agent_id, "issue": "no input_keys — check user template"})

        for ver, system_text in versions.items():
            if not system_text:
                report["flags"].append({"agent_id": agent_id, "version": ver, "issue": "empty system prompt"})
                continue
            sys_path = agent_dir / f"{ver}_system.txt"
            user_path = agent_dir / f"{ver}_user.j2"
            if sys_path.exists() and not force:
                pass
            else:
                sys_path.write_text(system_text, encoding="utf-8")
            if not user_path.exists() or force:
                user_path.write_text(user_j2, encoding="utf-8")

        report["written"].append({"agent_id": agent_id, "agent_name": agent_name, "versions": list(versions.keys())})

    out_report = ROOT / "evals" / "reports" / "agent_matrix" / "prompt_extraction_report.json"
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport: {out_report}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    extract(force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
