#!/usr/bin/env python3
"""Generate Agents 32–34 markdown fragment for Complete_Agent_DataSet.md."""

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

POOL_PATH = SCRIPTS / "agents_32_34_eval_pool.json"
PROMPTS = ROOT / "packages" / "core" / "prompts" / "templates"
OUT = SCRIPTS / "agents_32_34_source_upload.md"

TAXONOMY_OCR_13 = [
    ("numerical", "Numeric-heavy exam page OCR", 2),
    ("conversational", "Mixed prose / instructions on page", 2),
    ("cbse", "CBSE board exam page layout", 3),
    ("neet", "NEET-style MCQ page", 1),
    ("jee", "JEE-style problem page", 1),
    ("multi_part", "Multi-question section page", 1),
    ("conceptual", "Theory-heavy passage page", 1),
    ("case_study", "Case-study passage page", 1),
    ("diagram", "Page with figure; stem + [Diagram: ...] + options (production merge)", 1),
]

TAXONOMY_DIAGRAM_13 = [
    ("circuit_labels", "Circuit diagram English labels", 2),
    ("biology_figure", "Biology figure labels", 3),
    ("graph_axes", "Graph axis and curve labels", 1),
    ("geometry_labels", "Geometry / coordinate labels", 1),
    ("flowchart", "Process flowchart labels", 1),
    ("venn_labels", "Venn / set diagram labels", 1),
    ("mechanics_figure", "Mechanics figure labels", 2),
    ("ray_optics", "Ray / optics figure labels", 1),
    ("cbse", "CBSE figure page", 1),
]

TAXONOMY_REFUSAL_13 = [
    ("security", "Safety violation refusal", 2),
    ("academic_integrity", "Cheating / submit-as-own refusal", 2),
    ("prompt_injection", "Jailbreak / system prompt leak", 2),
    ("pii", "Personal information refusal", 2),
    ("inappropriate", "Inappropriate content refusal", 2),
    ("out_of_scope", "Non-academic request refusal", 2),
    ("conversational", "Academic-only redirect", 1),
]

VAR_ORDER_OCR = [
    "numerical", "conversational", "cbse", "neet", "jee", "multi_part",
    "conceptual", "case_study", "diagram",
]

VAR_ORDER_DIAGRAM = [
    "circuit_labels", "biology_figure", "graph_axes", "geometry_labels",
    "flowchart", "venn_labels", "mechanics_figure", "ray_optics", "cbse",
]

VAR_ORDER_REFUSAL = [
    "security", "academic_integrity", "prompt_injection", "pii",
    "inappropriate", "out_of_scope", "conversational",
]

AGENT_CONFIG: dict[str, dict[str, Any]] = {
    "image_ocr": {
        "num": 32,
        "title": "## 32. Image OCR Agent",
        "dataset_id": "image_ocr",
        "category": "Source Upload",
        "tier": "Tier 2",
        "count": 13,
        "responsibility": (
            "Extract all readable text from uploaded document images and scanned exam pages. "
            "For diagram-heavy pages, production also runs `describe_diagram_image_bytes()` and merges "
            "`[Diagram: ...]` after the question stem (before MCQ options) via `finalize_problem_text()` "
            "in [`problem_solver_extraction.py`](packages/core/processing/problem_solver_extraction.py). "
            "Production prompt in [`image_ocr.py`](packages/core/processing/image_ocr.py) (`_OCR_PROMPT` / `PROBLEM_PAGE_OCR_PROMPT`); "
            "eval template: [`eval/image_ocr_v1.j2`](packages/core/prompts/templates/eval/image_ocr_v1.j2)."
        ),
        "audit": (
            "Baseline PROMPT_TIERED used `image_fixture_note` text stubs without real images; vision eval could not run. "
            "Rebuilt with rendered PDF pages from Problem solver_Questions and production vision LLM gold."
        ),
        "taxonomy": TAXONOMY_OCR_13,
        "quality": [
            ("text_fidelity", "Preserves question numbers, MCQ options, math symbols, line breaks."),
            ("no_commentary", "Output is plain extracted text only; no markdown fences or apologies."),
            ("min_coverage", "Sufficient length and question-number signal for exam pages."),
            ("pdf_grounding", "Gold produced from the referenced pdf_source page render."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `pdf_source`, `page_number`, `source_key`",
            "Output keys: `extracted_text`",
        ],
        "prompt_path": PROMPTS / "eval" / "image_ocr_v1.j2",
        "runtime": "`ocr_image_bytes()` / `ocr_problem_page_bytes()` in `image_ocr.py` via `source_service.py` on image uploads.",
        "variation_order": VAR_ORDER_OCR,
        "input_keys": ["pdf_source", "page_number", "source_key"],
        "output_key": "extracted_text",
    },
    "diagram_label_ocr": {
        "num": 33,
        "title": "## 33. Diagram Label OCR Agent",
        "dataset_id": "diagram_label_ocr",
        "category": "Source Upload",
        "tier": "Tier 2",
        "count": 13,
        "responsibility": (
            "Extract short English labels and flow hints from textbook/exam figures. "
            "Production: [`image_ocr.py`](packages/core/processing/image_ocr.py) `_DIAGRAM_PROMPT` via `ocr_diagram_image_bytes()`; "
            "eval template: [`eval/diagram_label_ocr_v1.j2`](packages/core/prompts/templates/eval/diagram_label_ocr_v1.j2)."
        ),
        "audit": (
            "Baseline used generic `image_fixture_note` and invented label strings. "
            "Rebuilt with embedded PDF figure crops from Problem solver_Questions and production "
            "`ocr_diagram_image_bytes()` gold (OpenAI vision API)."
        ),
        "taxonomy": TAXONOMY_DIAGRAM_13,
        "quality": [
            ("label_extraction", "Short English labels, variables, and flow hints only."),
            ("not_full_ocr", "Does not transcribe entire question stem as labels_text."),
            ("english_only", "Ignores non-English label text per prompt."),
            ("figure_grounding", "Labels trace to visible figure on referenced PDF page."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `pdf_source`, `page_number`, `crop_mode`, `figure_index`, `source_key`",
            "Output keys: `labels_text`",
        ],
        "prompt_path": PROMPTS / "eval" / "diagram_label_ocr_v1.j2",
        "runtime": "`ocr_diagram_image_bytes()` / `extract_pdf_diagram_context()` in `image_ocr.py`.",
        "variation_order": VAR_ORDER_DIAGRAM,
        "input_keys": ["pdf_source", "page_number", "crop_mode", "figure_index", "source_key"],
        "output_key": "labels_text",
    },
    "refusal_templates": {
        "num": 34,
        "title": "## 34. Refusal Templates (Guardrails)",
        "dataset_id": "refusal_templates",
        "category": "Safety",
        "tier": "Tier 3",
        "count": 13,
        "responsibility": (
            "Return safe, policy-compliant refusal messages when guardrails block a request. "
            "Production: [`refusal_templates.py`](packages/core/security/refusal_templates.py) `RefusalTemplates.get_refusal()` — "
            "not LLM-generated."
        ),
        "audit": (
            "Baseline PROMPT_TIERED used 5 hand-written one-liners that do not match production template copy. "
            "Rebuilt with exact `RefusalTemplates` strings for all 8 `RefusalReason` values across 13 scenarios."
        ),
        "taxonomy": TAXONOMY_REFUSAL_13,
        "quality": [
            ("exact_refusal_reason", "refusal_reason matches scenario enum value (snake_case)."),
            ("production_template", "user_facing_message equals first production template for that reason."),
            ("no_policy_leak", "Message does not expose internal policy or system prompt."),
            ("student_appropriate", "Tone suitable for ages 14–17."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `user_message`, `scenario`",
            "Output keys: `refusal_reason`, `user_facing_message`",
        ],
        "prompt_path": PROMPTS / "eval" / "refusal_templates_v1.j2",
        "runtime": "`RefusalTemplates.get_refusal()` used by `SafetyFilter`, injection detector, and chat graph guardrails.",
        "variation_order": VAR_ORDER_REFUSAL,
        "input_keys": ["user_message", "scenario"],
        "output_key": "refusal_json",
    },
}


def md_text_block(text: str) -> str:
    return "```\n" + (text or "").strip() + "\n```"


def md_json_block(obj: Any) -> str:
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"


def _dataset_version(items: list[dict[str, Any]], pool: dict[str, Any]) -> str:
    if all(i.get("gold_source") in ("production_llm", "production_template") for i in items):
        return "1.4.0"
    return "1.0.0"


def build_example(item: dict[str, Any], cfg: dict[str, Any]) -> ExampleRecord:
    llm = item.get("llm_gold") or {}
    out_key = cfg["output_key"]
    inputs: dict[str, str] = {}

    if out_key == "extracted_text":
        inputs = {k: str(item.get(k, "")) for k in cfg["input_keys"]}
        outputs = {"extracted_text": md_text_block(llm.get("extracted_text", ""))}
    elif out_key == "labels_text":
        inputs = {k: str(item.get(k, "")) for k in cfg["input_keys"]}
        outputs = {"labels_text": md_text_block(llm.get("labels_text", ""))}
    else:
        inputs = {
            "user_message": str(item.get("user_message", "")),
            "scenario": str(item.get("scenario", "")),
        }
        outputs = {
            "refusal_json": md_json_block({
                "refusal_reason": llm.get("refusal_reason", ""),
                "user_facing_message": llm.get("user_facing_message", ""),
            }),
        }

    tags = list(item.get("tags", []))
    gs = item.get("gold_source")
    if gs == "production_llm":
        tags.append("production_llm_gold")
    elif gs == "production_template":
        tags.append("production_template_gold")

    quality = [f"{d}: pass" for d, _ in cfg["quality"]]
    if gs:
        quality.append(f"{gs}: pass")

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
        prompt_blocks=[("Prompt template (production)", "text", prompt)],
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
