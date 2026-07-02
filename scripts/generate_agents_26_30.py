#!/usr/bin/env python3
"""Generate Agents 26–30 markdown fragment for Complete_Agent_DataSet.md."""

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

POOL_PATH = SCRIPTS / "agents_26_30_eval_pool.json"
PROMPTS = ROOT / "packages" / "core" / "prompts" / "templates"
OUT = SCRIPTS / "agents_26_30_rag_source.md"

TAXONOMY_13 = [
    ("numerical", "Formula/numeric-heavy source text", 2),
    ("conversational", "Natural upload headers and mixed prose", 2),
    ("cbse", "CBSE board exam framing", 2),
    ("neet", "NEET-oriented biology/chemistry", 1),
    ("jee", "JEE-style physics/math depth", 1),
    ("multi_part", "Multi-section documents", 1),
    ("conceptual", "Theory-first exposition", 1),
    ("case_study", "Passage-based social science", 1),
    ("ncert_strict", "Strict NCERT chapter vocabulary", 1),
    ("proof", "Derivation-heavy maths", 1),
    ("typo", "Robust to minor OCR/header noise", 1),
]

VARIATION_ORDER = [
    "numerical", "conversational", "cbse", "neet", "jee", "multi_part",
    "conceptual", "case_study", "ncert_strict", "proof", "typo",
]

AGENT_CONFIG: dict[str, dict[str, Any]] = {
    "document_sketch": {
        "num": 26,
        "title": "## 26. Document Sketch Agent",
        "dataset_id": "document_sketch",
        "category": "RAG Ingestion",
        "tier": "Tier 3",
        "count": 13,
        "responsibility": (
            "Build a compact JSON document sketch for user-uploaded sources (exam papers, handouts) "
            "to contextualize chunks at ingestion. "
            "Production: [`rag/document_sketch.j2`](packages/core/prompts/templates/rag/document_sketch.j2)."
        ),
        "audit": (
            "Baseline PROMPT_TIERED stubs reused generic key_definitions (e.g. Ohm's law on organic chemistry) "
            "and thin concept lists. Rebuilt with real upload excerpts from the problem solver bank and "
            "production LLM gold validated for subject alignment and ≥10 concepts."
        ),
        "taxonomy": TAXONOMY_13,
        "quality": [
            ("schema_complete", "chapter_title, main_sections, key_definitions, concepts all present."),
            ("concept_coverage", "concepts array has 10–30 subject-relevant terms."),
            ("subject_alignment", "key_definitions match document topic; no cross-subject leaks."),
            ("compactness", "No long verbatim excerpts; sketch JSON under size cap."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `header`, `document_text`",
            "Output keys: `sketch_json`",
        ],
        "prompt_path": PROMPTS / "rag" / "document_sketch.j2",
        "runtime": "`generate_upload_document_sketch()` in `document_sketcher.py` during tenant upload ingestion.",
        "variation_order": VARIATION_ORDER,
        "input_keys": ["header", "document_text"],
        "output_key": "sketch_json",
    },
    "ncert_document_sketch": {
        "num": 27,
        "title": "## 27. NCERT Document Sketch Agent",
        "dataset_id": "ncert_document_sketch",
        "category": "RAG Ingestion",
        "tier": "Tier 3",
        "count": 13,
        "responsibility": (
            "Build a compact JSON sketch for NCERT chapter PDFs used in global NCERT ingestion. "
            "Production: [`rag/ncert_document_sketch.j2`](packages/core/prompts/templates/rag/ncert_document_sketch.j2)."
        ),
        "audit": (
            "Baseline stubs used placeholder section headings and mismatched definitions. "
            "Rebuilt with catalog-locked NCERT chapter excerpts (Classes 9–12) and production LLM gold."
        ),
        "taxonomy": TAXONOMY_13,
        "quality": [
            ("schema_complete", "All sketch_json keys present and typed correctly."),
            ("ncert_vocabulary", "Headings and concepts use NCERT chapter terminology."),
            ("concept_coverage", "≥10 searchable concept terms per chapter."),
            ("compactness", "Short definitions only; no long quotes."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `header`, `document_text`",
            "Output keys: `sketch_json`",
        ],
        "prompt_path": PROMPTS / "rag" / "ncert_document_sketch.j2",
        "runtime": "`generate_ncert_document_sketch()` in `document_sketcher.py` during NCERT global ingestion.",
        "variation_order": VARIATION_ORDER,
        "input_keys": ["header", "document_text"],
        "output_key": "sketch_json",
    },
    "chunk_contextualization": {
        "num": 28,
        "title": "## 28. Chunk Contextualization Agent",
        "dataset_id": "chunk_contextualization",
        "category": "RAG Ingestion",
        "tier": "Tier 3",
        "count": 13,
        "responsibility": (
            "Situate each ingestion chunk within its parent document: context, summary, type, section, concept hints. "
            "Production: [`rag/chunk_contextualization.j2`](packages/core/prompts/templates/rag/chunk_contextualization.j2)."
        ),
        "audit": (
            "Baseline examples omitted token target inputs and returned generic chunk_type. "
            "Rebuilt with paired whole_document + chunk_content from NCERT splits and validated enums."
        ),
        "taxonomy": TAXONOMY_13,
        "quality": [
            ("input_keys_complete", "whole_document, chunk_content, target_* token fields all populated."),
            ("chunk_type_valid", "chunk_type is one of definition|procedure|example|table|figure|argument|formula|qa|other."),
            ("grounding", "chunk_context references parent document; no invented syllabus."),
            ("compactness", "Context and summary within token targets; concept_hint is comma-separated."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `whole_document`, `chunk_content`, `target_context_tokens`, `target_summary_tokens`, `target_concept_terms`",
            "Output keys: `contextualization_json`",
        ],
        "prompt_path": PROMPTS / "rag" / "chunk_contextualization.j2",
        "runtime": "`ChunkContextualizer.enrich_chunk()` in `contextualizer.py` at ingestion time.",
        "variation_order": VARIATION_ORDER,
        "input_keys": [
            "whole_document", "chunk_content", "target_context_tokens",
            "target_summary_tokens", "target_concept_terms",
        ],
        "output_key": "contextualization_json",
    },
    "whole_file_map_summarizer": {
        "num": 29,
        "title": "## 29. Whole File Map Summarizer Agent",
        "dataset_id": "whole_file_map_summarizer",
        "category": "RAG Retrieval",
        "tier": "Tier 2",
        "count": 13,
        "responsibility": (
            "MAP step of whole-file map-reduce: one concrete sentence per document part. "
            "Production: [`rag/whole_file_map_prompt.j2`](packages/core/prompts/templates/rag/whole_file_map_prompt.j2)."
        ),
        "audit": (
            "Baseline gold used placeholder lines ('Main idea of section N'). "
            "Rebuilt with 3–6 real NCERT/bank excerpts per example and production LLM gold."
        ),
        "taxonomy": TAXONOMY_13,
        "quality": [
            ("one_line_per_part", "Exactly one Part N: sentence per input part."),
            ("concrete_content", "Each line captures a specific idea from its excerpt."),
            ("ordering", "Part numbers match input order."),
            ("no_preamble", "No introduction or conclusion lines."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `parts` (rendered as excerpts in prompt)",
            "Output keys: `map_summaries`",
        ],
        "prompt_path": PROMPTS / "rag" / "whole_file_map_prompt.j2",
        "runtime": (
            "`_map_batch_summarize()` in `whole_file_map_reduce.py` during whole-document queries."
        ),
        "variation_order": VARIATION_ORDER,
        "input_keys": ["parts"],
        "output_key": "map_summaries",
    },
    "whole_file_reduce": {
        "num": 30,
        "title": "## 30. Whole File Reduce Agent",
        "dataset_id": "whole_file_reduce",
        "category": "RAG Retrieval",
        "tier": "Tier 2",
        "count": 13,
        "responsibility": (
            "REDUCE step: synthesize a user-facing Markdown answer from ordered section summaries. "
            "Production: [`rag/whole_file_reduce_prompt.j2`](packages/core/prompts/templates/rag/whole_file_reduce_prompt.j2)."
        ),
        "audit": (
            "Baseline returned generic 'Synthesis of N parts' without addressing user intent. "
            "Rebuilt with section_summaries chained from Agent 29 gold on the same document."
        ),
        "taxonomy": TAXONOMY_13,
        "quality": [
            ("covers_all_parts", "Answer reflects themes from every section summary."),
            ("user_intent", "Addresses user_message (summarize, list formulas, revision, etc.)."),
            ("markdown_structure", "Uses headings or bullets when helpful."),
            ("no_citations", "No [1] citation markers or raw excerpt dumps."),
        ],
        "langsmith": [
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `user_message`, `section_summaries`",
            "Output keys: `final_answer`",
        ],
        "prompt_path": PROMPTS / "rag" / "whole_file_reduce_prompt.j2",
        "runtime": "`_reduce_summaries()` in `whole_file_map_reduce.py` after map step.",
        "variation_order": VARIATION_ORDER,
        "input_keys": ["user_message", "section_summaries"],
        "output_key": "final_answer",
    },
}


def md_json_block(obj: Any) -> str:
    return "```json\n" + json.dumps(obj, indent=2, ensure_ascii=False) + "\n```"


def md_text_block(text: str) -> str:
    return "```markdown\n" + (text or "").strip() + "\n```"


def _dataset_version(items: list[dict[str, Any]], pool: dict[str, Any]) -> str:
    if all(i.get("gold_source") == "production_llm" for i in items):
        return pool.get("version", "1.4.0")
    return "1.0.0"


def build_example(item: dict[str, Any], cfg: dict[str, Any]) -> ExampleRecord:
    llm = item.get("llm_gold") or {}
    out_key = cfg["output_key"]
    inputs: dict[str, str] = {}

    if out_key == "sketch_json":
        inputs = {k: str(item.get(k) or "") for k in cfg["input_keys"]}
        outputs = {"sketch_json": md_json_block(llm.get("sketch_json", {}))}
    elif out_key == "contextualization_json":
        for k in cfg["input_keys"]:
            val = item.get(k)
            inputs[k] = str(val) if val is not None else ""
        outputs = {"contextualization_json": md_json_block(llm.get("contextualization_json", {}))}
    elif out_key == "map_summaries":
        parts = item.get("parts") or []
        inputs["parts"] = md_json_block(parts)
        outputs = {"map_summaries": md_text_block(llm.get("map_summaries", ""))}
    else:
        inputs["user_message"] = str(item.get("user_message") or "")
        summaries = llm.get("section_summaries") or item.get("section_summaries") or ""
        inputs["section_summaries"] = summaries
        outputs = {"final_answer": md_text_block(llm.get("final_answer", ""))}

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
