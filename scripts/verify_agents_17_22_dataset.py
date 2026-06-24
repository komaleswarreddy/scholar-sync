#!/usr/bin/env python3
"""Verify Agents 17-22 dataset quality in Complete_Agent_DataSet.md."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

TARGETS = {
    "problem_dna_analyzer": 30,
    "explain_from_basics": 30,
    "show_best_approach": 30,
    "show_missing_idea": 30,
    "help_me_solve_it": 30,
    "problem_solver_followup": 15,
}

VARIATION_QUOTAS = {
    "numerical": 7, "jee": 5, "neet": 2, "multi_part": 1, "cbse": 5,
    "proof": 2, "diagram": 2, "ncert_strict": 1, "conceptual": 3, "case_study": 2,
}

PLACEHOLDER_PATTERNS = [
    r"Restate problem",
    r"Worked answer with units",
    r"LLM-judge",
    r"Continuation without losing context",
    r"Key insight without full solution",
    r"Completed answer",
    r"\bTBD\b",
    r"Student applied an unrelated formula without identifying the governing concept",
    r"Student tried random formula without identifying given quantities",
]

GENERIC_STUDENT_ATTEMPT = "student applied an unrelated formula without identifying the governing concept"

SOURCE_KEYS = {
    "cbse_biology", "cbse_mathematics", "cbse_physics",
    "jee_april_2026", "jee_jan_2026",
    "neet_botany", "neet_chemistry", "neet_physics", "neet_zoology",
}

FOLLOWUP_ACTIONS = {
    "GIVE_SIMILAR_PROBLEM", "REVEAL_SOLUTION", "SHOW_BEST_APPROACH", "SHOW_SHORTER_VERSION",
    "EXPLAIN_CONCEPT_AGAIN", "SHOW_NEXT_HINT", "START_TUTOR_SESSION",
}

AGENT_SECTIONS = [
    ("## 17. Problem DNA Analyzer", "problem_dna_analyzer"),
    ("## 18. Explain From Basics Coach", "explain_from_basics"),
    ("## 19. Show Best Approach Coach", "show_best_approach"),
    ("## 20. Show Missing Idea Coach", "show_missing_idea"),
    ("## 21. Help Me Solve It Coach", "help_me_solve_it"),
    ("## 22. Problem Solver Follow-up Handler", "problem_solver_followup"),
]

MIN_PROMPT_FENCE = 80


def section_slice(text: str, start_marker: str, end_marker: str | None) -> str:
    start = text.find(start_marker)
    if start < 0:
        return ""
    if end_marker:
        end = text.find(end_marker, start + len(start_marker))
        return text[start:end] if end > 0 else text[start:]
    return text[start:]


def count_examples(section: str, prefix: str) -> int:
    return len(re.findall(rf"`{prefix}-\d{{3}}`", section))


def main() -> int:
    text = MD.read_text(encoding="utf-8")
    errors: list[str] = []

    for marker, agent_id in AGENT_SECTIONS:
        next_idx = AGENT_SECTIONS.index((marker, agent_id)) + 1
        end = AGENT_SECTIONS[next_idx][0] if next_idx < len(AGENT_SECTIONS) else None
        section = section_slice(text, marker, end)
        if not section:
            errors.append(f"Missing section: {marker}")
            continue
        n = count_examples(section, agent_id)
        if n != TARGETS[agent_id]:
            errors.append(f"{agent_id}: expected {TARGETS[agent_id]} examples, found {n}")

    block17 = text[text.find("## 17."):]
    # Exclude audit-finding lines (they quote baseline placeholder phrases intentionally)
    block_no_audit = re.sub(
        r"\*\*Audit finding \(baseline v1\.0\.0\):\*\*[^\n]*\n",
        "",
        block17,
    )
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, block_no_audit):
            errors.append(f"Placeholder pattern found in gold: {pat}")

    if re.search(r"\*\*Evaluators:\*\*", text[text.find("## 17."):]):
        errors.append("Evaluators lines present in Agents 17-22")

    agent17 = section_slice(text, "## 17. Problem DNA Analyzer", "## 18.")
    m = re.search(r"```jinja2\n(.+?)```", agent17, re.S)
    if not m or len(m.group(1)) < MIN_PROMPT_FENCE:
        errors.append("Agent 17 prompt fence too short")

    # Variation quotas per agent 17-21
    for agent_num in range(17, 22):
        start = f"## {agent_num}."
        end = f"## {agent_num + 1}."
        sec = section_slice(text, start, end)
        vars_found = Counter(re.findall(r"- \*\*Variation:\*\* (\S+)", sec))
        for var, quota in VARIATION_QUOTAS.items():
            if vars_found.get(var, 0) != quota:
                errors.append(f"Agent {agent_num} variation `{var}`: expected {quota}, got {vars_found.get(var, 0)}")

    # Unique problem texts across 17-22
    problems = re.findall(
        r"\*\*Problem Text Normalized:\*\*\s*\n\n(.+?)\n\n\*\*",
        text[text.find("## 17."):],
        re.S,
    )
    norms = [re.sub(r"\s+", " ", p.strip().lower()) for p in problems]
    if len(norms) != len(set(norms)):
        errors.append(f"Duplicate problem_text_normalized in 17-22: {len(norms) - len(set(norms))}")

    # Source PDF tags
    tags_found = set()
    for m in re.finditer(r"source_pdf_([\w_]+)", text[text.find("## 17."):]):
        tags_found.add(m.group(1))
    missing_sources = SOURCE_KEYS - tags_found
    if missing_sources:
        errors.append(f"Missing source_pdf tags: {missing_sources}")

    # Agent 20: no student_attempt inputs (generic trap framing)
    sec20 = section_slice(text, "## 20. Show Missing Idea Coach", "## 21.")
    if re.search(r"\*\*Student Attempt:\*\*", sec20):
        errors.append("show_missing_idea: student_attempt inputs must be removed")
    stuck_sections = len(re.findall(r"Where Most Students Get Stuck", sec20))
    if stuck_sections < 25:
        errors.append(f"show_missing_idea: expected >=25 'Where Most Students Get Stuck' sections, found {stuck_sections}")

    # Agent 21: cumulative gold for interaction_count >= 1
    sec21 = section_slice(text, "## 21.", "## 22.")
    ic_counts = Counter(re.findall(r"\*\*Interaction Count:\*\*\s*\n\n(\d+)", sec21))
    for branch in ("0", "1", "2"):
        if ic_counts.get(branch, 0) < 8:
            errors.append(f"help_me_solve_it interaction_count {branch}: need >=8, got {ic_counts.get(branch, 0)}")
    for block in re.findall(r"\*\*Interaction Count:\*\*\s*\n\n([12])\s*\n\n.*?\*\*Coach Json:\*\*\s*\n\n```json\n(\{.*?\})\n```", sec21, re.S):
        ic_val, raw_json = block
        try:
            coach = json.loads(raw_json)
        except json.JSONDecodeError:
            errors.append(f"help_me_solve_it interaction_count {ic_val}: invalid coach_json")
            continue
        sections = coach.get("sections") or []
        headings = [str(s.get("heading", "")).lower() for s in sections if isinstance(s, dict)]
        if int(ic_val) >= 1 and not any("problem decode" in h for h in headings):
            errors.append("help_me_solve_it: interaction_count>=1 gold missing Problem decode section")
        if int(ic_val) >= 1 and not any("feedback" in h for h in headings):
            errors.append("help_me_solve_it: interaction_count>=1 gold missing Feedback section")
        hist = coach.get("checkpointHistory") or []
        if int(ic_val) >= 1 and not hist:
            errors.append(f"help_me_solve_it interaction_count {ic_val}: empty checkpointHistory")
        elif int(ic_val) == 1 and not hist[0].get("studentChoice"):
            errors.append("help_me_solve_it: checkpoint 1 missing studentChoice in history")
        elif int(ic_val) == 2 and len(hist) < 2:
            errors.append("help_me_solve_it: interaction_count 2 needs 2 checkpoint history entries")

    # Agent 22 actions
    sec22 = text[text.find("## 22."):]
    actions = set(re.findall(r"\*\*Action:\*\*\s*\n\n(\S+)", sec22))
    missing_actions = FOLLOWUP_ACTIONS - actions
    if missing_actions:
        errors.append(f"Missing follow-up actions: {missing_actions}")

    # JSON blocks present
    json_blocks = len(re.findall(r"```json\n\{", text[text.find("## 17."):]))
    if json_blocks < 165:
        errors.append(f"Expected >=165 JSON gold blocks, found {json_blocks}")

    print("Agents 17-22 verification")
    for marker, agent_id in AGENT_SECTIONS:
        sec = section_slice(text, marker, None)
        print(f"  {agent_id}: {count_examples(sec, agent_id)} examples")

    if errors:
        print("\nFAILURES:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nRESULT: All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
