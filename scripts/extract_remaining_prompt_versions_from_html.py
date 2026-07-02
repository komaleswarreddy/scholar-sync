#!/usr/bin/env python3
"""Extract Version A/B/C from Reference dataset/reamingin promts.html -> prompt_versions/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HTML_PATH = ROOT / "Reference dataset" / "reamingin promts.html"
OUT_ROOT = ROOT / "evals" / "agent_eval" / "prompt_versions"
MANIFEST_PATH = ROOT / "evals" / "datasets" / "prompt_tiered" / "manifest.json"

# Map sheet Agent column -> agent_id (by name — OCR uses sno 31/32 in this HTML, not manifest 32/33)
AGENT_NAME_TO_ID: dict[str, str] = {
    "Help Me Solve It Coach": "help_me_solve_it",
    "Problem Solver Follow-up Handler": "problem_solver_followup",
    "Tutor Notebook Bootstrap Agent": "tutor_notebook_bootstrap",
    "Tutor Follow-up Questions Agent": "tutor_follow_up_questions",
    "Source Question Extraction Agent": "source_question_extraction",
    "Image OCR Agent": "image_ocr",
    "Diagram Label OCR Agent": "diagram_label_ocr",
}

USER_NUDGE = (
    "Produce the output now, following the instructions above. "
    "Return only the required format (JSON only if the instructions specify JSON), "
    "with no extra commentary.\n"
)

OCR_USER_IMAGE = """{# Text harness — pre-OCR page text (Option A gold copy) #}
## Document page text
{{ image_text }}

Transcribe exactly per system instructions. Plain text only, no commentary.
"""

OCR_USER_DIAGRAM = """{# Text harness — figure label text (Option A gold copy) #}
## Figure labels / crop text
{{ figure_crop }}

Return labels exactly per system instructions. Plain text only.
"""


def _clean(text: str) -> str:
    if text is None:
        return ""
    s = str(text).strip()
    if s.lower() == "nan":
        return ""
    return s


def _normalize_system(text: str) -> str:
    t = _clean(text)
    if t.upper().startswith("SYSTEM:"):
        t = t[7:].lstrip("\n").strip()
    return t


def _load_input_keys(agent_id: str) -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = next(d for d in manifest["datasets"] if d["dataset_id"] == agent_id)
    ds = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
    return list((ds.get("langsmith") or {}).get("input_keys") or [])


def _build_user_j2(agent_id: str, input_keys: list[str]) -> str:
    if agent_id == "image_ocr":
        return OCR_USER_IMAGE
    if agent_id == "diagram_label_ocr":
        return OCR_USER_DIAGRAM

    lines = ["{# Auto-generated from dataset langsmith.input_keys #}", ""]
    label_map = {
        "problem_text_normalized": "Problem",
        "interaction_count": "Interaction count",
        "ncert_context": "NCERT context",
        "student_choice": "Student choice",
        "action": "Action",
        "solving_mode": "Solving mode",
        "user_follow_up": "Student follow-up",
        "class_num": "Class",
        "subject_label": "Subject",
        "chapter_no": "Chapter number",
        "chapter_title": "Chapter title",
        "concept": "Focus concept",
        "document_text": "Document text",
        "last_user_message": "Last user message",
        "last_assistant_message": "Last assistant message",
        "chapter_context": "Chapter context",
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
    if not HTML_PATH.is_file():
        raise SystemExit(f"HTML not found: {HTML_PATH}")

    t = pd.read_html(HTML_PATH, encoding="utf-8")[0].iloc[1:].copy()
    t.columns = ["rownum", "sno", "agent", "va", "vb", "vc", "col_g", "col_h"]

    report: dict = {"written": [], "skipped": [], "flags": []}
    seen_agents: set[str] = set()

    for _, r in t.iterrows():
        agent_name = _clean(r["agent"])
        agent_id = AGENT_NAME_TO_ID.get(agent_name)
        if not agent_id:
            continue
        if agent_id in seen_agents:
            continue
        seen_agents.add(agent_id)

        versions = {
            "v1": _normalize_system(r["va"]),
            "v2": _normalize_system(r["vb"]),
            "v3": _normalize_system(r["vc"]),
        }
        if not all(versions.values()):
            report["flags"].append(
                {"agent_id": agent_id, "agent_name": agent_name, "issue": "missing A/B/C in HTML"}
            )
            continue

        agent_dir = OUT_ROOT / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        input_keys = _load_input_keys(agent_id)
        user_j2 = _build_user_j2(agent_id, input_keys)

        for ver, system_text in versions.items():
            sys_path = agent_dir / f"{ver}_system.txt"
            user_path = agent_dir / f"{ver}_user.j2"
            if force or not sys_path.exists():
                sys_path.write_text(system_text + "\n", encoding="utf-8")
            if force or not user_path.exists():
                user_path.write_text(user_j2, encoding="utf-8")

        report["written"].append(
            {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "sno": _clean(r["sno"]),
                "chars": {k: len(v) for k, v in versions.items()},
            }
        )

    missing = set(AGENT_NAME_TO_ID.values()) - seen_agents
    if missing:
        report["flags"].append({"issue": "agents not found in HTML", "agent_ids": sorted(missing)})

    out_report = ROOT / "evals" / "reports" / "agent_matrix" / "remaining_prompt_extraction_report.json"
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport: {out_report}")
    if len(report["written"]) != len(AGENT_NAME_TO_ID):
        raise SystemExit(f"Expected {len(AGENT_NAME_TO_ID)} agents, wrote {len(report['written'])}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    extract(force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
