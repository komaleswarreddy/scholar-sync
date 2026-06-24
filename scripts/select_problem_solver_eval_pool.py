#!/usr/bin/env python3
"""Select 165 unique eval problems for Agents 17-22 from the question bank."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from problem_solver_gold_authors import expert_solution

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from packages.core.processing.problem_solver_extraction import is_verified_diagram_problem  # noqa: E402
BANK_PATH = SCRIPTS / "problem_solver_question_bank.json"
OUT_PATH = SCRIPTS / "problem_solver_eval_pool.json"
COMPLETE_MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

AGENTS = [
    ("problem_dna_analyzer", 17, 30),
    ("explain_from_basics", 18, 30),
    ("show_best_approach", 19, 30),
    ("show_missing_idea", 20, 30),
    ("help_me_solve_it", 21, 30),
    ("problem_solver_followup", 22, 15),
]

VARIATION_SLOTS_17_21 = (
    ["numerical"] * 7 + ["jee"] * 5 + ["neet"] * 2 + ["multi_part"] * 1 + ["cbse"] * 5
    + ["proof"] * 2 + ["diagram"] * 2 + ["ncert_strict"] * 1 + ["conceptual"] * 3 + ["case_study"] * 2
)

SOURCE_MINIMUMS = {
    "cbse_biology": 12,
    "cbse_mathematics": 10,
    "cbse_physics": 12,
    "jee_april_2026": 18,
    "jee_jan_2026": 18,
    "neet_botany": 18,
    "neet_chemistry": 18,
    "neet_physics": 18,
    "neet_zoology": 18,
}

FOLLOWUP_ACTIONS = [
    "GIVE_SIMILAR_PROBLEM", "REVEAL_SOLUTION", "SHOW_BEST_APPROACH", "SHOW_SHORTER_VERSION",
    "EXPLAIN_CONCEPT_AGAIN", "SHOW_NEXT_HINT", "START_TUTOR_SESSION",
]
SOLVING_MODES = ["HELP_ME_SOLVE_IT", "EXPLAIN_FROM_BASICS", "SHOW_BEST_APPROACH", "SHOW_MISSING_IDEA"]


SOURCE_SUBJECT = {
    "cbse_biology": "biology",
    "cbse_mathematics": "mathematics",
    "cbse_physics": "physics",
    "neet_botany": "biology",
    "neet_zoology": "biology",
    "neet_chemistry": "chemistry",
    "neet_physics": "physics",
    "jee_april_2026": "physics",
    "jee_jan_2026": "physics",
}


def apply_source_subject(q: dict[str, Any]) -> dict[str, Any]:
    q = dict(q)
    sk = q.get("source_key", "")
    if sk in SOURCE_SUBJECT:
        q["subject"] = SOURCE_SUBJECT[sk]
    return q


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def load_existing_problems() -> set[str]:
    if not COMPLETE_MD.exists():
        return set()
    text = COMPLETE_MD.read_text(encoding="utf-8")
    cutoff = text.find("## 17. Problem DNA Analyzer")
    if cutoff > 0:
        text = text[:cutoff]
    found = set()
    for m in re.finditer(r"\*\*Problem Text Normalized:\*\*\s*\n\n(.+?)\n\n\*\*", text, re.S):
        found.add(normalize(m.group(1)))
    return found


def map_variation(q: dict[str, Any]) -> str:
    fmt = q.get("format", "")
    exam = q.get("exam_type", "")
    text = q.get("problem_text_normalized", "").lower()
    if is_verified_diagram_problem(q.get("problem_text_normalized", "")):
        return "diagram"
    if fmt == "proof":
        return "proof"
    if fmt == "multi_part":
        return "multi_part"
    if fmt == "case_study":
        return "case_study"
    if fmt == "conceptual":
        return "conceptual"
    if fmt == "numerical":
        return "numerical"
    if "ncert" in text and exam == "cbse":
        return "ncert_strict"
    if exam == "jee":
        return "jee"
    if exam == "neet" or fmt == "assertion_reason":
        return "neet"
    if exam == "cbse":
        return "cbse"
    return "numerical"


def quality_score(q: dict[str, Any]) -> float:
    text = q.get("problem_text_normalized", "")
    score = min(len(text) / 200.0, 3.0)
    if q.get("extraction_method") == "text":
        score += 1.0
    if re.search(r"\([A-D]\)|\([1-4]\)", text):
        score += 0.5
    if q.get("has_image"):
        score += 0.3
    return score


def build_slots() -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for agent_id, agent_num, count in AGENTS:
        if agent_id == "problem_solver_followup":
            for i in range(count):
                slots.append({
                    "agent_id": agent_id,
                    "agent_num": agent_num,
                    "variation": "follow_up",
                    "action": FOLLOWUP_ACTIONS[i % len(FOLLOWUP_ACTIONS)],
                    "solving_mode": SOLVING_MODES[i % len(SOLVING_MODES)],
                })
        else:
            variations = VARIATION_SLOTS_17_21
            for i, var in enumerate(variations):
                ic = i % 3  # 0,1,2 cycle for help_me_solve_it
                slots.append({
                    "agent_id": agent_id,
                    "agent_num": agent_num,
                    "variation": var,
                    "interaction_count": ic if agent_id == "help_me_solve_it" else None,
                    "student_choice": "A" if agent_id == "help_me_solve_it" and ic in (1, 2) else "",
                })
    return slots


def select_pool(questions: list[dict[str, Any]], existing: set[str]) -> list[dict[str, Any]]:
    slots = build_slots()
    used_texts: set[str] = set(existing)
    used_ids: set[str] = set()
    source_counts: Counter[str] = Counter()
    by_var: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for q in questions:
        q = apply_source_subject(q)
        norm = normalize(q["problem_text_normalized"])
        if norm in used_texts or len(norm) < 40:
            continue
        var = map_variation(q)
        q = dict(q)
        q["_variation"] = var
        q["_score"] = quality_score(q)
        by_var[var].append(q)
    for var in by_var:
        by_var[var].sort(key=lambda x: -x["_score"])

    selected: list[dict[str, Any]] = []
    # First pass: satisfy source minimums
    for source, minimum in SOURCE_MINIMUMS.items():
        need = minimum
        for q in sorted(questions, key=lambda x: -quality_score(x)):
            q = apply_source_subject(q)
            if need <= 0:
                break
            if q.get("source_key") != source:
                continue
            norm = normalize(q["problem_text_normalized"])
            if norm in used_texts or q["id"] in used_ids:
                continue
            var = map_variation(q)
            slot_idx = next(
                (i for i, s in enumerate(slots) if s["variation"] == var and "question" not in s),
                None,
            )
            if slot_idx is None:
                slot_idx = next((i for i, s in enumerate(slots) if "question" not in s), None)
            if slot_idx is None:
                continue
            slot = slots[slot_idx]
            gold = expert_solution(
                q["problem_text_normalized"], q["subject"], q["format"], q["exam_type"]
            )
            entry = {**slot, **q, "gold": gold, "variation": slot["variation"]}
            selected.append(entry)
            slots[slot_idx]["question"] = True
            used_texts.add(norm)
            used_ids.add(q["id"])
            source_counts[source] += 1
            need -= 1

    # Second pass: fill remaining slots
    for i, slot in enumerate(slots):
        if slot.get("question"):
            continue
        var = slot["variation"]
        if var == "diagram":
            candidates = [q for q in by_var.get("diagram", []) if is_verified_diagram_problem(q.get("problem_text_normalized", ""))]
        else:
            candidates = by_var.get(var, []) + by_var.get("cbse", []) + by_var.get("numerical", [])
        picked = None
        for q in candidates:
            q = apply_source_subject(q)
            norm = normalize(q["problem_text_normalized"])
            if norm in used_texts or q["id"] in used_ids:
                continue
            picked = q
            break
        if not picked:
            for q in sorted(questions, key=lambda x: -quality_score(apply_source_subject(x))):
                q = apply_source_subject(q)
                norm = normalize(q["problem_text_normalized"])
                if norm not in used_texts and q["id"] not in used_ids:
                    picked = q
                    break
        if not picked:
            raise RuntimeError(f"Could not fill slot {i} variation={var}")
        gold = expert_solution(
            picked["problem_text_normalized"], picked["subject"], picked["format"], picked["exam_type"]
        )
        entry = {**slot, **picked, "gold": gold, "variation": slot["variation"]}
        selected.append(entry)
        used_texts.add(normalize(picked["problem_text_normalized"]))
        used_ids.add(picked["id"])
        source_counts[picked["source_key"]] += 1
        slots[i]["question"] = True

    # Assign example ids
    agent_counters: Counter[str] = Counter()
    for entry in selected:
        agent_counters[entry["agent_id"]] += 1
        n = agent_counters[entry["agent_id"]]
        entry["example_id"] = f"{entry['agent_id']}-{n:03d}"
    return selected


def main() -> int:
    if not BANK_PATH.exists():
        print(f"Run extract_problem_solver_questions.py first. Missing {BANK_PATH}", file=sys.stderr)
        return 1
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    questions = bank["questions"]
    existing = load_existing_problems()
    pool = select_pool(questions, existing)
    payload = {
        "version": "1.1.0",
        "total": len(pool),
        "source_counts": dict(Counter(p["source_key"] for p in pool)),
        "agent_counts": dict(Counter(p["agent_id"] for p in pool)),
        "items": pool,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(pool)} eval items to {OUT_PATH}")
    print("Agent counts:", payload["agent_counts"])
    print("Source counts:", payload["source_counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
