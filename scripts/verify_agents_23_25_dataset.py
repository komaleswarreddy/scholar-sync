#!/usr/bin/env python3
"""Strict verification for Agents 23–25 dataset."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
POOL = SCRIPTS / "agents_23_25_eval_pool.json"
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

TARGETS = {
    "tutor_notebook_bootstrap": 15,
    "tutor_follow_up_questions": 30,
    "source_question_extraction": 30,
}

PLACEHOLDER_PATTERNS = [
    r"Explain Electricity from NCERT\.",
    r"Numerical practice on",
    r"Where is this in NCERT exam\?",
    r"Common mistake about",
    r"NCERT Class \d+ Science Ch\.12: Electricity\.\s*$",
    r"Define Ohm's law\.\s*\"fullText\"",
]


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def main() -> int:
    failures: list[str] = []
    if not POOL.exists():
        print(f"Missing {POOL}", file=sys.stderr)
        return 1
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    items = pool["items"]

    by_agent = Counter(i["agent_id"] for i in items)
    for aid, n in TARGETS.items():
        if by_agent[aid] != n:
            failures.append(f"{aid}: expected {n} examples, got {by_agent[aid]}")

    llm_count = sum(1 for i in items if i.get("gold_source") == "production_llm" and i.get("llm_gold"))
    if llm_count != 75:
        failures.append(f"production_llm gold: {llm_count}/75")

    # Unique inputs globally
    input_norms: list[str] = []
    for i in items:
        if i["agent_id"] == "source_question_extraction":
            input_norms.append(normalize(i["document_text"][:400]))
        elif i["agent_id"] == "tutor_follow_up_questions":
            input_norms.append(normalize(i["user_message"] + "|" + i["assistant_message"]))
        else:
            input_norms.append(normalize(i.get("ncert_context", "")))
    if len(input_norms) != len(set(input_norms)):
        failures.append(f"duplicate inputs in pool: {len(input_norms) - len(set(input_norms))}")

    for i in items:
        ex = i["example_id"]
        gold = i.get("llm_gold")
        if not gold:
            failures.append(f"{ex}: missing llm_gold")
            continue
        raw = json.dumps(gold)
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, raw, re.I):
                failures.append(f"{ex}: placeholder pattern {pat}")

        if i["agent_id"] == "tutor_notebook_bootstrap":
            bj = gold.get("bootstrap_json", {})
            sugg = bj.get("suggestions", [])
            labels = [s.get("label") for s in sugg if isinstance(s, dict)]
            if len(sugg) != 4:
                failures.append(f"{ex}: bootstrap suggestions count {len(sugg)}")
            if len(set(labels)) < 3:
                failures.append(f"{ex}: duplicate suggestion labels")
            summary = bj.get("opening_summary", "")
            if "### Key topics" not in summary or "### Exam highlights" not in summary:
                failures.append(f"{ex}: opening_summary missing required sections")
            studio = bj.get("studio_recommendations", [])
            auto = sum(1 for s in studio if s.get("auto_generate"))
            if auto != 2:
                failures.append(f"{ex}: studio auto_generate count {auto} != 2")

        elif i["agent_id"] == "tutor_follow_up_questions":
            fu = gold.get("follow_ups", [])
            if len(fu) != 3:
                failures.append(f"{ex}: follow_ups count {len(fu)}")
            if any(len(str(x)) > 90 for x in fu):
                failures.append(f"{ex}: follow_up exceeds 90 chars")
            if any("numerical practice on" in str(x).lower() for x in fu):
                failures.append(f"{ex}: generic follow_up template")

        elif i["agent_id"] == "source_question_extraction":
            sections = gold.get("sections_json", {}).get("sections", [])
            qcount = sum(len(s.get("questions", [])) for s in sections)
            doc = i["document_text"]
            if qcount < 1:
                failures.append(f"{ex}: zero questions extracted")
            if "Define Ohm's law" in json.dumps(sections) and "Ohm" not in doc and "ohm" not in doc.lower():
                failures.append(f"{ex}: hallucinated Ohm's law gold")

    concept_count = sum(1 for i in items if i["agent_id"] == "tutor_follow_up_questions" and i.get("concept"))
    if concept_count < 10:
        failures.append(f"follow_up concept coverage low: {concept_count}/30 (target ~12)")

    if MD.exists() and "## 23." in MD.read_text(encoding="utf-8"):
        md_block = MD.read_text(encoding="utf-8")[MD.read_text(encoding="utf-8").find("## 23."):]
        if "Version | 1.4.0" not in md_block and "| Version | 1.4.0 |" not in md_block:
            if "Version | 1.4.2" not in md_block and "| Version | 1.4.2 |" not in md_block:
                if llm_count == 75:
                    failures.append("MD missing v1.4.2 version markers for agents 23-25")

    print(f"Agents 23-25 verify: {len(failures)} failure(s)")
    for f in failures[:25]:
        print(f"  FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
