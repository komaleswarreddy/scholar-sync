#!/usr/bin/env python3
"""Remove bad diagrams from agents 17-25 eval pools and question bank."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from packages.core.processing.problem_solver_extraction import (  # noqa: E402
    is_verified_diagram_problem,
    sanitize_problem_diagrams,
)

BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
POOL_17_22 = SCRIPTS / "problem_solver_eval_pool.json"
POOL_23_25 = SCRIPTS / "agents_23_25_eval_pool.json"

# Verified diagram bank items (stem-consistent [Diagram:] blocks).
VERIFIED_DIAGRAM_IDS = [
    "cbse_mathematics-p6-q51",
    "cbse_mathematics-p5-q47",
    "jee_april_2026-p8-q29",
    "jee_jan_2026-p15-q36",
    "jee_jan_2026-p20-q47",
    "cbse_biology-p15-q51",
    "jee_jan_2026-p29-q64",
    "jee_april_2026-p12-q43",
    "jee_jan_2026-p14-q33",
    "neet_physics-p19-q27",
    "jee_april_2026-p11-q39",
    "neet_physics-p32-q49",
    "jee_april_2026-p9-q33",
]

# Diagram variation slots that must use verified diagram problems only.
DIAGRAM_VARIATION_REPLACEMENTS: dict[str, str] = {
    "problem_dna_analyzer-009": "cbse_mathematics-p5-q47",
    "explain_from_basics-015": "jee_april_2026-p12-q43",
    "show_best_approach-013": "jee_jan_2026-p14-q33",
    "show_missing_idea-006": "neet_physics-p19-q27",
    "help_me_solve_it-002": "jee_april_2026-p11-q39",
    "help_me_solve_it-003": "neet_physics-p32-q49",
}

# Agent 25: reclassify mis-tagged diagram_ref examples.
AGENT25_RECLASSIFY: dict[str, str] = {
    "source_question_extraction-013": "mcq_section",
    "source_question_extraction-018": "mcq_section",
    "source_question_extraction-012": "numerical",
    "source_question_extraction-027": "footer_noise",
}

# Agents 23-24: diagram variation without visual inputs → conceptual.
TUTOR_DIAGRAM_RECLASSIFY: dict[str, str] = {
    "tutor_notebook_bootstrap-003": "numerical",
    "tutor_notebook_bootstrap-014": "conceptual",
    "tutor_follow_up_questions-003": "cbse",
    "tutor_follow_up_questions-014": "conceptual",
    "tutor_follow_up_questions-028": "conceptual",
}


def _bank_fields(q: dict) -> dict:
    text = sanitize_problem_diagrams(q.get("problem_text_normalized", ""))
    has_diag = "[diagram:" in text.lower() and is_verified_diagram_problem(text)
    fmt = q.get("format", "")
    if fmt == "diagram" and not has_diag:
        if re.search(r"\(i\)|\(ii\)|case study|passage", text, re.I):
            fmt = "case_study"
        elif re.search(r"\b(find|calculate|compute)\b", text, re.I):
            fmt = "numerical"
        else:
            fmt = "jee" if q.get("exam_type") == "jee" else "mcq"
    return {
        "problem_text_normalized": text,
        "has_image": has_diag,
        "format": fmt if not has_diag or fmt == "diagram" else fmt,
    }


def sanitize_bank(bank: dict) -> int:
    changed = 0
    for q in bank["questions"]:
        patch = _bank_fields(q)
        if patch["problem_text_normalized"] != q.get("problem_text_normalized"):
            changed += 1
        q.update(patch)
        if patch["has_image"] and q.get("format") not in ("diagram", "case_study"):
            q["format"] = "diagram"
    bank["version"] = "1.4.4"
    return changed


def _apply_bank_item(item: dict, bank_q: dict) -> None:
    """Copy bank question fields into eval pool item (preserve gold)."""
    for key in (
        "id", "source_pdf", "source_key", "page", "exam_type", "subject",
        "class_num", "format", "problem_text_normalized", "has_image",
        "extraction_method", "raw_text", "tags", "diagram_description",
        "corruption_flags",
    ):
        if key in bank_q:
            item[key] = bank_q[key]


def sanitize_pool_17_22(pool: dict, bank_by_id: dict[str, dict]) -> tuple[int, int]:
    stripped = 0
    swapped = 0
    used_ids = {it["id"] for it in pool["items"]}

    for item in pool["items"]:
        old = item.get("problem_text_normalized", "")
        new = sanitize_problem_diagrams(old)
        if new != old:
            item["problem_text_normalized"] = new
            stripped += 1
        item["has_image"] = is_verified_diagram_problem(new)
        if not item["has_image"]:
            item["diagram_description"] = ""

        ex_id = item.get("example_id", "")
        if item.get("variation") == "diagram":
            if not is_verified_diagram_problem(new):
                target_id = DIAGRAM_VARIATION_REPLACEMENTS.get(ex_id)
                if not target_id:
                    for vid in VERIFIED_DIAGRAM_IDS:
                        if vid not in used_ids or vid == item.get("id"):
                            target_id = vid
                            break
                if target_id and target_id in bank_by_id:
                    bank_q = bank_by_id[target_id]
                    used_ids.discard(item.get("id", ""))
                    _apply_bank_item(item, bank_q)
                    used_ids.add(target_id)
                    swapped += 1
            elif ex_id in DIAGRAM_VARIATION_REPLACEMENTS:
                pass  # already good

    pool["version"] = "1.4.4"
    return stripped, swapped


def sanitize_pool_23_25(pool: dict) -> int:
    changed = 0
    for item in pool.get("items", []):
        ex_id = item.get("example_id", "")
        if ex_id in TUTOR_DIAGRAM_RECLASSIFY:
            item["variation"] = TUTOR_DIAGRAM_RECLASSIFY[ex_id]
            tags = [t for t in item.get("tags", []) if t != "diagram"]
            item["tags"] = tags
            changed += 1
        if item.get("agent_num") == 25 and ex_id in AGENT25_RECLASSIFY:
            item["variation"] = AGENT25_RECLASSIFY[ex_id]
            tags = [t for t in item.get("tags", []) if t != "diagram_ref"]
            item["tags"] = tags
            changed += 1
        doc = item.get("document_text")
        if doc and "[diagram:" in doc.lower():
            cleaned = sanitize_problem_diagrams(doc)
            if cleaned != doc:
                item["document_text"] = cleaned
                changed += 1
    pool["version"] = "1.4.4"
    return changed


def main() -> int:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    bank_changed = sanitize_bank(bank)
    BANK_PATH.write_text(json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8")
    bank_by_id = {q["id"]: q for q in bank["questions"]}

    pool = json.loads(POOL_17_22.read_text(encoding="utf-8"))
    stripped, swapped = sanitize_pool_17_22(pool, bank_by_id)
    POOL_17_22.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")

    changed_23_25 = 0
    if POOL_23_25.exists():
        pool25 = json.loads(POOL_23_25.read_text(encoding="utf-8"))
        changed_23_25 = sanitize_pool_23_25(pool25)
        POOL_23_25.write_text(json.dumps(pool25, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Bank: sanitized {bank_changed} questions (v1.4.4)")
    print(f"Pool 17-22: stripped {stripped}, swapped diagram slots {swapped}")
    print(f"Pool 23-25: reclassified/sanitized {changed_23_25}")

    # Verify diagram variation slots
    failures: list[str] = []
    for item in pool["items"]:
        if item.get("variation") != "diagram":
            continue
        if not is_verified_diagram_problem(item.get("problem_text_normalized", "")):
            failures.append(item.get("example_id", "?"))
    if failures:
        print(f"WARNING: diagram variation still invalid: {failures}", file=sys.stderr)
        return 1
    print("All diagram variation examples verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
