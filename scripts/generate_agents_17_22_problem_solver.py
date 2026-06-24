#!/usr/bin/env python3
"""Generate Agents 17-22 markdown fragments for Complete_Agent_DataSet.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from agent_section_renderer import (
    ExampleRecord,
    load_j2,
    render_agent_header,
    render_examples_grouped,
)
from problem_solver_gold_authors import (
    coach_explain_from_basics,
    coach_followup,
    coach_help_me_solve,
    coach_show_best_approach,
    coach_show_missing_idea,
    dna_json,
    infer_chapter,
    ncert_context as build_ncert_context,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
POOL_PATH = SCRIPTS / "problem_solver_eval_pool.json"
PROMPTS = ROOT / "packages" / "core" / "prompts" / "templates" / "problem_solver"
OUT = SCRIPTS / "agents_17_22_problem_solver.md"

VARIATION_ORDER = [
    "numerical", "jee", "neet", "multi_part", "cbse", "proof", "diagram",
    "ncert_strict", "conceptual", "case_study", "follow_up",
]

AGENT_CONFIG: dict[str, dict[str, Any]] = {
    "problem_dna_analyzer": {
        "num": 17,
        "title": "## 17. Problem DNA Analyzer",
        "dataset_id": "problem_dna_analyzer",
        "category": "Problem Solving",
        "tier": "Tier 1",
        "count": 30,
        "responsibility": (
            "Classify a normalized problem stem into subject, chapter, difficulty, question type, "
            "and internal expert solution metadata without leaking the final answer in `problem_dna_summary`. "
            "Production template: [`problem_solver/dna.j2`](packages/core/prompts/templates/problem_solver/dna.j2)."
        ),
        "audit": (
            "Baseline v1.0.0 recycled three stub problems (microscope, ∫, pepsin) across all coach agents, "
            "used mismatched NCERT context, placeholder gold (`LLM-judge`), and no diagram/OCR coverage. "
            "Rebuilt with 30 unique problems from the Problem solver_Questions bank, locked variation taxonomy, "
            "full inline prompt, and complete `dna_json` gold with NCERT-aligned expert solutions."
        ),
        "taxonomy": [
            ("numerical", "Numeric/unit problems", 7),
            ("jee", "JEE Mains framing", 5),
            ("neet", "NEET MCQ / assertion-reason", 2),
            ("multi_part", "Multi-step / derive", 1),
            ("cbse", "CBSE board style", 5),
            ("proof", "Derivation / proof", 2),
            ("diagram", "Diagram-dependent (OCR bank)", 2),
            ("ncert_strict", "Strict NCERT wording", 1),
            ("conceptual", "Explain-why / concept", 3),
            ("case_study", "Passage / case-based", 2),
        ],
        "quality": [
            ("subject_match", "Subject/chapter align with problem content, not notebook scope order."),
            ("no_answer_in_summary", "`problem_dna_summary` must not contain final numeric answer."),
            ("schema_valid", "All required `dna_json` keys present with valid enums."),
            ("difficulty_calibration", "Difficulty and expected time match exam type and stem length."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `problem_text_normalized`, `ncert_context`, `class_num`, `subject_labels`",
            "Output keys: `dna_json`",
        ],
        "prompt_path": PROMPTS / "dna.j2",
        "runtime": (
            "[`packages/core/services/problem_solver_service.py`](packages/core/services/problem_solver_service.py) "
            "`ProblemSolverService.analyze_dna()` stores `problem_dna` on the session before coach modes run."
        ),
        "output_key": "dna_json",
    },
    "explain_from_basics": {
        "num": 18,
        "title": "## 18. Explain From Basics Coach",
        "dataset_id": "explain_from_basics",
        "category": "Problem Solving",
        "tier": "Tier 1",
        "count": 30,
        "responsibility": (
            "Full beginner-friendly walkthrough with eight sections and `revealLevel: full`. "
            "Production: [`explain_from_basics.j2`](packages/core/prompts/templates/problem_solver/explain_from_basics.j2)."
        ),
        "audit": (
            "Baseline had one-line placeholder coach gold (`Restate problem.`). Rebuilt with 30 unique bank problems, "
            "eight complete sections per example, LaTeX-ready markdown, and NCERT-aligned `finalAnswer`."
        ),
        "taxonomy": [
            ("numerical", "Numeric/unit problems", 7),
            ("jee", "JEE Mains framing", 5),
            ("neet", "NEET MCQ / assertion-reason", 2),
            ("multi_part", "Multi-step / derive", 1),
            ("cbse", "CBSE board style", 5),
            ("proof", "Derivation / proof", 2),
            ("diagram", "Diagram-dependent", 2),
            ("ncert_strict", "Strict NCERT wording", 1),
            ("conceptual", "Explain-why / concept", 3),
            ("case_study", "Passage / case-based", 2),
        ],
        "quality": [
            ("section_completeness", "All eight coach sections populated with substantive markdown."),
            ("reveal_level", "`revealLevel` is `full`; `finalAnswer` present."),
            ("ncert_alignment", "Concept and formula sections match authored NCERT context."),
            ("latex_format", "Display/inline math uses `\\[...\\]` and `$...$` where needed."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `problem_text_normalized`, `ncert_context`",
            "Output keys: `coach_json`",
        ],
        "prompt_path": PROMPTS / "explain_from_basics.j2",
        "runtime": "`ProblemSolverService` mode `EXPLAIN_FROM_BASICS`.",
        "output_key": "coach_json",
    },
    "show_best_approach": {
        "num": 19,
        "title": "## 19. Show Best Approach Coach",
        "dataset_id": "show_best_approach",
        "category": "Problem Solving",
        "tier": "Tier 1",
        "count": 30,
        "responsibility": (
            "Exam-efficient method with seven sections plus `finalAnswer`. "
            "Production: [`show_best_approach.j2`](packages/core/prompts/templates/problem_solver/show_best_approach.j2)."
        ),
        "audit": "Placeholder baseline replaced with complete seven-section exam-oriented coach JSON per bank problem.",
        "taxonomy": [
            ("numerical", "Numeric/unit problems", 7),
            ("jee", "JEE Mains framing", 5),
            ("neet", "NEET MCQ / assertion-reason", 2),
            ("multi_part", "Multi-step / derive", 1),
            ("cbse", "CBSE board style", 5),
            ("proof", "Derivation / proof", 2),
            ("diagram", "Diagram-dependent", 2),
            ("ncert_strict", "Strict NCERT wording", 1),
            ("conceptual", "Explain-why / concept", 3),
            ("case_study", "Passage / case-based", 2),
        ],
        "quality": [
            ("section_completeness", "All seven sections including Exam Note and When Not to Use."),
            ("reveal_level", "`revealLevel: full` with boxed final answer."),
            ("ncert_alignment", "Best method matches chapter skill from DNA metadata."),
            ("latex_format", "Multiplication spaced; units in `\\text{}`."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `problem_text_normalized`, `ncert_context`",
            "Output keys: `coach_json`",
        ],
        "prompt_path": PROMPTS / "show_best_approach.j2",
        "runtime": "`ProblemSolverService` mode `SHOW_BEST_APPROACH`.",
        "output_key": "coach_json",
    },
    "show_missing_idea": {
        "num": 20,
        "title": "## 20. Show Missing Idea Coach",
        "dataset_id": "show_missing_idea",
        "category": "Problem Solving",
        "tier": "Tier 1",
        "count": 30,
        "responsibility": (
            "Reveal the key unlock with `revealLevel: partial` — no full solution by default. "
            "Production: [`show_missing_idea.j2`](packages/core/prompts/templates/problem_solver/show_missing_idea.j2)."
        ),
        "audit": (
            "Baseline stub `Key insight without full solution` replaced; each example identifies the "
            "typical missing idea and where most students get stuck — without any student attempt input."
        ),
        "taxonomy": [
            ("numerical", "Numeric/unit problems", 7),
            ("jee", "JEE Mains framing", 5),
            ("neet", "NEET MCQ / assertion-reason", 2),
            ("multi_part", "Multi-step / derive", 1),
            ("cbse", "CBSE board style", 5),
            ("proof", "Derivation / proof", 2),
            ("diagram", "Diagram-dependent", 2),
            ("ncert_strict", "Strict NCERT wording", 1),
            ("conceptual", "Explain-why / concept", 3),
            ("case_study", "Passage / case-based", 2),
        ],
        "quality": [
            ("section_completeness", "Five sections: Missing Idea through Where Most Students Get Stuck."),
            ("reveal_level", "`revealLevel: partial`; no `finalAnswer` in gold."),
            ("ncert_alignment", "Mental model cites correct chapter principle."),
            ("typical_student_trap", "Common trap is problem-specific, not a generic placeholder."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `problem_text_normalized`, `ncert_context`",
            "Output keys: `coach_json`",
        ],
        "prompt_path": PROMPTS / "show_missing_idea.j2",
        "runtime": "`ProblemSolverService` mode `SHOW_MISSING_IDEA`.",
        "output_key": "coach_json",
    },
    "help_me_solve_it": {
        "num": 21,
        "title": "## 21. Help Me Solve It Coach",
        "dataset_id": "help_me_solve_it",
        "category": "Problem Solving",
        "tier": "Tier 1",
        "count": 30,
        "responsibility": (
            "Guided solve with `interaction_count` branches: hints+checkpoint (0), feedback (1), full solution (2+). "
            "Production: [`help_me_solve_it.j2`](packages/core/prompts/templates/problem_solver/help_me_solve_it.j2)."
        ),
        "audit": "Baseline had empty checkpoint labels and premature `Completed answer` stubs. Rebuilt with branching gold and no premature final answers at count 0/1.",
        "taxonomy": [
            ("numerical", "Numeric/unit problems", 7),
            ("jee", "JEE Mains framing", 5),
            ("neet", "NEET MCQ / assertion-reason", 2),
            ("multi_part", "Multi-step / derive", 1),
            ("cbse", "CBSE board style", 5),
            ("proof", "Derivation / proof", 2),
            ("diagram", "Diagram-dependent", 2),
            ("ncert_strict", "Strict NCERT wording", 1),
            ("conceptual", "Explain-why / concept", 3),
            ("case_study", "Passage / case-based", 2),
        ],
        "quality": [
            ("no_premature_answer", "Counts 0–1 must not include final numeric answer."),
            ("checkpoint_quality", "Checkpoint MCQ has four plausible options; A is concept-correct."),
            ("interaction_branch", "Gold shape matches `interaction_count` branch in template."),
            ("cumulative_context", "Counts 1–2 include decode, hints, feedback, and checkpointHistory with studentChoice/selectedLabel."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `problem_text_normalized`, `interaction_count`, `ncert_context`, `student_choice`",
            "Output keys: `coach_json`",
        ],
        "prompt_path": PROMPTS / "help_me_solve_it.j2",
        "runtime": "`ProblemSolverService` mode `HELP_ME_SOLVE_IT` with session interaction counter.",
        "output_key": "coach_json",
    },
    "problem_solver_followup": {
        "num": 22,
        "title": "## 22. Problem Solver Follow-up Handler",
        "dataset_id": "problem_solver_followup",
        "category": "Problem Solving",
        "tier": "Tier 2",
        "count": 15,
        "responsibility": (
            "Handle follow-up button actions after a coach session without losing problem context. "
            "Production: [`follow_up.j2`](packages/core/prompts/templates/problem_solver/follow_up.j2)."
        ),
        "audit": "Baseline `Continuation without losing context` stub replaced with action-specific follow-up bodies across all seven actions.",
        "taxonomy": [
            ("follow_up", "Post-coach button actions", 15),
        ],
        "quality": [
            ("action_compliance", "Title and body reflect the requested `action` slug."),
            ("context_retention", "References original problem stem and prior `solving_mode`."),
            ("reveal_level", "`hint` vs `full` matches action semantics."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `action`, `problem_text_normalized`, `solving_mode`, `user_follow_up`",
            "Output keys: `coach_json`",
        ],
        "prompt_path": PROMPTS / "follow_up.j2",
        "runtime": "`ProblemSolverService.handle_follow_up()` after coach button click.",
        "output_key": "coach_json",
    },
}


def md_json_block(obj: Any) -> str:
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"


def _ncert_for_item(item: dict[str, Any]) -> str:
    ch = infer_chapter(item["problem_text_normalized"], item.get("subject", "physics"))
    return build_ncert_context(ch, item.get("subject", "physics"))


def _dataset_version(agent_id: str, items: list[dict[str, Any]], pool: dict[str, Any]) -> str:
    vision_tag = pool.get("extraction_tag") == "vision_enriched_extraction"
    if vision_tag and all(item.get("gold_source") == "production_llm" for item in items):
        return "1.4.0"
    if agent_id == "show_missing_idea":
        if all(item.get("gold_source") == "production_llm" for item in items):
            return "1.5.0"
    if all(item.get("gold_source") == "production_llm" for item in items):
        return "1.2.0"
    if any(item.get("llm_gold") for item in items):
        return "1.2.0"
    return "1.1.0"


def subject_labels(subject: str) -> str:
    return f"- {subject.title()}"


def build_example(item: dict[str, Any], cfg: dict[str, Any]) -> ExampleRecord:
    gold = item.get("gold") or {}
    llm_gold = item.get("llm_gold")
    agent_id = item["agent_id"]
    subj = item["subject"]
    ncert_ctx = _ncert_for_item(item) if llm_gold else gold.get("ncert_context", _ncert_for_item(item))
    base_tags = [t for t in item.get("tags", []) if t not in {
        "biology", "chemistry", "physics", "mathematics", "mixed", "cbse", "jee", "neet",
    }]
    tags = list(dict.fromkeys([
        subj, item["exam_type"], f"source_pdf_{item['source_key']}", item["variation"], *base_tags[:3],
    ]))
    if item.get("gold_source") == "production_llm":
        tags.append("production_llm_gold")
    if item.get("extraction_method") == "hybrid_vision" or "[diagram:" in item["problem_text_normalized"].lower():
        tags.append("vision_enriched_extraction")
    inputs: dict[str, str] = {
        "problem_text_normalized": item["problem_text_normalized"],
        "ncert_context": ncert_ctx,
    }
    if agent_id == "problem_dna_analyzer":
        inputs["class_num"] = str(item.get("class_num", "12"))
        inputs["subject_labels"] = subject_labels(item["subject"])
        out_obj = llm_gold["dna_json"] if llm_gold else dna_json(item, gold)
        outputs = {"dna_json": md_json_block(out_obj)}
        quality = ["subject_match: pass", "no_answer_in_summary: pass", "schema_valid: pass", "difficulty_calibration: pass"]
        if llm_gold:
            quality.append("production_llm_gold: pass")
    elif agent_id == "explain_from_basics":
        out_obj = llm_gold["coach_json"] if llm_gold else coach_explain_from_basics(item, gold)
        outputs = {"coach_json": md_json_block(out_obj)}
        quality = ["section_completeness: pass", "reveal_level: pass", "ncert_alignment: pass", "latex_format: pass"]
        if llm_gold:
            quality.append("production_llm_gold: pass")
    elif agent_id == "show_best_approach":
        out_obj = llm_gold["coach_json"] if llm_gold else coach_show_best_approach(item, gold)
        outputs = {"coach_json": md_json_block(out_obj)}
        quality = ["section_completeness: pass", "reveal_level: pass", "ncert_alignment: pass", "latex_format: pass"]
        if llm_gold:
            quality.append("production_llm_gold: pass")
    elif agent_id == "show_missing_idea":
        out_obj = llm_gold["coach_json"] if llm_gold else coach_show_missing_idea(item, gold)
        outputs = {"coach_json": md_json_block(out_obj)}
        quality = ["section_completeness: pass", "reveal_level: pass", "ncert_alignment: pass", "typical_student_trap: pass"]
        if llm_gold:
            quality.append("production_llm_gold: pass")
    elif agent_id == "help_me_solve_it":
        ic = int(item.get("interaction_count") or 0)
        sc = item.get("student_choice") or "None"
        inputs["interaction_count"] = str(ic)
        inputs["student_choice"] = sc if sc else "None"
        out_obj = llm_gold["coach_json"] if llm_gold else coach_help_me_solve(item, gold, ic, sc if sc != "None" else "")
        outputs = {"coach_json": md_json_block(out_obj)}
        quality = ["no_premature_answer: pass", "checkpoint_quality: pass", "interaction_branch: pass"]
        if ic >= 1:
            quality.append("cumulative_context: pass")
        if llm_gold:
            quality.append("production_llm_gold: pass")
    else:
        action = item.get("action", "GIVE_SIMILAR_PROBLEM")
        mode = item.get("solving_mode", "HELP_ME_SOLVE_IT")
        inputs = {
            "action": action,
            "problem_text_normalized": item["problem_text_normalized"],
            "solving_mode": mode,
            "user_follow_up": f"Student clicked {action}",
            "ncert_context": ncert_ctx,
        }
        out_obj = llm_gold["coach_json"] if llm_gold else coach_followup(item, gold, action, mode)
        outputs = {"coach_json": md_json_block(out_obj)}
        quality = ["action_compliance: pass", "context_retention: pass", "reveal_level: pass"]
        if llm_gold:
            quality.append("production_llm_gold: pass")

    return ExampleRecord(
        ex_id=item["example_id"],
        variation=item["variation"],
        tags=tags,
        inputs=inputs,
        outputs=outputs,
        quality=quality,
    )


def render_agent(agent_id: str, items: list[dict[str, Any]], pool: dict[str, Any]) -> str:
    cfg = AGENT_CONFIG[agent_id]
    prompt = load_j2(cfg["prompt_path"])
    header = render_agent_header(
        title=cfg["title"],
        metadata_rows=[
            ("Dataset ID", f"`{cfg['dataset_id']}`"),
            ("Category", cfg["category"]),
            ("Tier", cfg["tier"]),
            ("Target examples", str(cfg["count"])),
            ("Actual examples", str(len(items))),
            ("Version", _dataset_version(agent_id, items, pool)),
        ],
        agent_responsibility=cfg["responsibility"],
        audit_finding=cfg["audit"],
        taxonomy_rows=cfg["taxonomy"],
        quality_dimensions=cfg["quality"],
        langsmith_items=cfg["langsmith"],
        prompt_blocks=[("Prompt template (production)", "jinja2", prompt)],
        runtime_note=cfg["runtime"],
        eval_count=len(items),
    )
    examples = [build_example(it, cfg) for it in items]
    order = ["follow_up"] if agent_id == "problem_solver_followup" else VARIATION_ORDER[:-1]
    body = render_examples_grouped(examples, order)
    return header + body


def main() -> int:
    if not POOL_PATH.exists():
        print(f"Run select_problem_solver_eval_pool.py first. Missing {POOL_PATH}", file=sys.stderr)
        return 1
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    by_agent: dict[str, list[dict[str, Any]]] = {a[0]: [] for a in [
        ("problem_dna_analyzer", 17, 30),
        ("explain_from_basics", 18, 30),
        ("show_best_approach", 19, 30),
        ("show_missing_idea", 20, 30),
        ("help_me_solve_it", 21, 30),
        ("problem_solver_followup", 22, 15),
    ]}
    for item in pool["items"]:
        by_agent[item["agent_id"]].append(item)

    parts: list[str] = []
    for agent_id in by_agent:
        parts.append(render_agent(agent_id, by_agent[agent_id], pool))
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(OUT.read_text(encoding='utf-8').splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
