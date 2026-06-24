#!/usr/bin/env python3
"""Generate Agents 23–25 markdown fragment for Complete_Agent_DataSet.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from agent_section_renderer import (
    ExampleRecord,
    load_j2,
    render_agent_header,
    render_examples_grouped,
)

POOL_PATH = SCRIPTS / "agents_23_25_eval_pool.json"
PROMPTS = ROOT / "packages" / "core" / "prompts" / "templates"
OUT = SCRIPTS / "agents_23_25_tutor_source.md"

AGENT_CONFIG: dict[str, dict[str, Any]] = {
    "tutor_notebook_bootstrap": {
        "num": 23,
        "title": "## 23. Tutor Notebook Bootstrap Agent",
        "dataset_id": "tutor_notebook_bootstrap",
        "category": "Tutor Mode",
        "tier": "Tier 2",
        "count": 15,
        "responsibility": (
            "Generate the first-open tutor notebook payload: opening summary (Markdown), "
            "four suggestion chips, and ranked studio recommendations with exactly two auto_generate tools. "
            "Production: [`tutor/notebook_bootstrap.j2`](packages/core/prompts/templates/tutor/notebook_bootstrap.j2)."
        ),
        "audit": (
            "Baseline v1.0.0 used duplicate suggestion chips, two-line opening summaries, "
            "mismatched NCERT context (e.g. photosynthesis text for digestion chapter), and generic quiz+flashcards "
            "for every subject. Rebuilt with catalog-locked class/chapter/concept scopes, aligned NCERT snippets, "
            "and production LLM gold via TutorNotebookBootstrapService sanitization rules."
        ),
        "taxonomy": [
            ("numerical", "Formula-heavy science chapters", 2),
            ("conversational", "Natural student onboarding", 2),
            ("diagram", "Visual / ray-diagram chapters", 2),
            ("cbse", "Board exam framing", 1),
            ("neet", "NEET-oriented biology/chemistry", 1),
            ("jee", "JEE-style physics depth", 1),
            ("multi_part", "Multi-concept chapters", 1),
            ("conceptual", "Theory-first chapters", 1),
            ("case_study", "Social science narrative", 1),
            ("ncert_strict", "Strict NCERT vocabulary", 1),
            ("typo", "Robust to minor typos in scope", 1),
            ("proof", "Derivation-heavy maths", 1),
        ],
        "quality": [
            ("opening_structure", "opening_summary has Summary, Key topics, Exam highlights, Ask me for full clarity."),
            ("suggestions_unique", "Exactly 4 unique label/prompt pairs, labels ≤28 chars."),
            ("studio_pair", "All 4 studio types present; exactly 2 auto_generate=true, subject-aware ranking."),
            ("ncert_grounding", "Facts in summary trace to ncert_context; no invented syllabus."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `class_num`, `subject_label`, `chapter_no`, `chapter_title`, `ncert_context`, `concept`",
            "Output keys: `bootstrap_json`",
        ],
        "prompt_path": PROMPTS / "tutor" / "notebook_bootstrap.j2",
        "runtime": "`TutorNotebookBootstrapService._generate_bootstrap_payload()` on notebook first open.",
        "variation_order": [
            "numerical", "conversational", "diagram", "cbse", "neet", "jee", "multi_part",
            "conceptual", "case_study", "ncert_strict", "typo", "proof",
        ],
        "input_keys": ["class_num", "subject_label", "chapter_no", "chapter_title", "ncert_context", "concept"],
        "output_key": "bootstrap_json",
    },
    "tutor_follow_up_questions": {
        "num": 24,
        "title": "## 24. Tutor Follow-up Questions Agent",
        "dataset_id": "tutor_follow_up_questions",
        "category": "Tutor Mode",
        "tier": "Tier 1",
        "count": 30,
        "responsibility": (
            "After each tutor exchange, suggest exactly three follow-up questions (≤90 chars) "
            "mixing clarify/deepen, apply/practice, and exam-angle. "
            "Production: [`tutor/follow_up_questions.j2`](packages/core/prompts/templates/tutor/follow_up_questions.j2)."
        ),
        "audit": (
            "Baseline v1.0.0 recycled generic templates with easy definitional exchanges. "
            "v1.5.0 rebuilds medium-difficulty multi-step exchanges, aligned scope, and production LLM gold."
        ),
        "taxonomy": [
            ("typo", "Student typo tolerance", 3),
            ("conversational", "Natural follow-ups", 4),
            ("diagram", "Post diagram explanation", 3),
            ("cbse", "Board exam angle", 3),
            ("neet", "NEET drill", 3),
            ("jee", "JEE application", 3),
            ("multi_part", "Multi-step topic", 2),
            ("conceptual", "Deepen understanding", 3),
            ("case_study", "Civics/social apply", 2),
            ("ncert_strict", "Strict NCERT tie-in", 2),
            ("proof", "Math reasoning", 2),
            ("edge_not_found", "RAG miss recovery", 1),
            ("numerical", "Numeric practice", 1),
        ],
        "quality": [
            ("three_follow_ups", "Exactly 3 questions, each ≤90 characters."),
            ("specificity", "No generic 'Tell me more'; tied to last exchange."),
            ("mix_roles", "Clarify, apply/practice, and exam-angle present."),
            ("scope_alignment", "Chapter title and subject match exchange content."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `user_message`, `assistant_message`, `class_num`, `subject_label`, `chapter_no`, `chapter_title`, `concept`",
            "Output keys: `follow_ups`",
        ],
        "prompt_path": PROMPTS / "tutor" / "follow_up_questions.j2",
        "runtime": "`TutorNotebookBootstrapService.generate_follow_ups()` after tutor chat turn.",
        "variation_order": [
            "typo", "conversational", "diagram", "cbse", "neet", "jee", "multi_part",
            "conceptual", "case_study", "ncert_strict", "proof", "edge_not_found", "numerical",
        ],
        "input_keys": ["user_message", "assistant_message", "class_num", "subject_label", "chapter_no", "chapter_title", "concept"],
        "output_key": "follow_ups",
    },
    "source_question_extraction": {
        "num": 25,
        "title": "## 25. Source Question Extraction Agent",
        "dataset_id": "source_question_extraction",
        "category": "Source Upload",
        "tier": "Tier 1",
        "count": 30,
        "responsibility": (
            "Parse uploaded exam/homework PDF text into structured question sections with previews, "
            "fullText, and confidence. Production: [`source_questions/extract.j2`](packages/core/prompts/templates/source_questions/extract.j2) "
            "via `SourceQuestionExtractionService`."
        ),
        "audit": (
            "Baseline v1.0.0 returned identical wrong gold ('Define Ohm's law') for every input including NEET/JEE papers. "
            "Rebuilt with real Problem solver_Questions page extracts plus curated CBSE/NEET/JEE snippets and production LLM gold "
            "normalized through `_normalize_sections()`."
        ),
        "taxonomy": [
            ("mcq_section", "Sectioned CBSE/NEET MCQ papers", 8),
            ("numerical", "Numeric JEE/CBSE problems", 6),
            ("assertion_reason", "Assertion-reason blocks", 2),
            ("multi_section", "Multiple labeled sections", 3),
            ("footer_noise", "Headers/footers to ignore", 4),
            ("diagram_ref", "Figure-referenced stems", 3),
            ("case_study", "Passage-based questions", 2),
            ("multi_part", "Sub-part (a)(b) questions", 2),
        ],
        "quality": [
            ("question_count", "All numbered questions in document_text captured."),
            ("full_text_complete", "fullText sufficient to solve; preview ≤120 chars."),
            ("no_hallucination", "No invented questions beyond document_text."),
            ("confidence_calibration", "low confidence when boundaries uncertain."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `document_text`",
            "Output keys: `sections_json`",
        ],
        "prompt_path": PROMPTS / "source_questions" / "extract.j2",
        "runtime": "`SourceQuestionExtractionService.extract_questions()` on uploaded PDF/image sources.",
        "variation_order": [
            "mcq_section", "numerical", "assertion_reason", "multi_section", "footer_noise",
            "neet", "jee", "cbse", "diagram_ref", "case_study", "multi_part", "low_confidence",
        ],
        "input_keys": ["document_text"],
        "output_key": "sections_json",
    },
}


def md_json_block(obj: Any) -> str:
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"


def _dataset_version(items: list[dict[str, Any]], pool: dict[str, Any]) -> str:
    if all(i.get("gold_source") == "production_llm" for i in items):
        return pool.get("version", "1.4.2")
    return "1.0.0"


def build_example(item: dict[str, Any], cfg: dict[str, Any]) -> ExampleRecord:
    inputs = {k: str(item.get(k) or "") for k in cfg["input_keys"] if k in item or k == "concept"}
    if "concept" in cfg["input_keys"] and item.get("concept") is None:
        inputs["concept"] = ""
    llm = item.get("llm_gold") or {}
    out_key = cfg["output_key"]
    if out_key == "follow_ups":
        outputs = {"follow_ups": md_json_block({"follow_ups": llm.get("follow_ups", [])})}
    elif out_key == "bootstrap_json":
        outputs = {"bootstrap_json": md_json_block(llm.get("bootstrap_json", {}))}
    else:
        outputs = {"sections_json": md_json_block(llm.get("sections_json", {}))}

    tags = list(item.get("tags", []))
    if item.get("gold_source") == "production_llm":
        tags.append("production_llm_gold")

    quality = [f"{d}: pass" for d, _ in cfg["quality"]]
    if item.get("gold_source") == "production_llm":
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
            ("Version", _dataset_version(items, pool)),
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
    body = render_examples_grouped(examples, cfg["variation_order"])
    return header + body


def main() -> int:
    if not POOL_PATH.exists():
        print(f"Missing {POOL_PATH}", file=sys.stderr)
        return 1
    pool = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    by_agent: dict[str, list[dict[str, Any]]] = {a: [] for a in AGENT_CONFIG}
    for item in pool["items"]:
        by_agent[item["agent_id"]].append(item)
    parts = [render_agent(aid, by_agent[aid], pool) for aid in AGENT_CONFIG]
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(OUT.read_text(encoding='utf-8').splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
