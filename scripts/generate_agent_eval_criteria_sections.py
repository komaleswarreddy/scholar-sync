#!/usr/bin/env python3
"""Generate per-agent evaluation criteria sections (all 33 agents, no grouping)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals" / "datasets" / "prompt_tiered" / "manifest.json"
MODELS = ROOT / "config" / "models.yaml"
OUT = ROOT / "evaluation" / "AGENT_EVAL_CRITERIA.generated.md"
MAIN = ROOT / "evaluation" / "AGENT_DATASETS_AND_SCORING.md"

START = "<!-- PER_AGENT_EVAL_CRITERIA_START -->"
END = "<!-- PER_AGENT_EVAL_CRITERIA_END -->"

EVALUATOR_METRICS: Dict[str, Dict[str, Any]] = {
    "router": {
        "class": "RouterEvaluator",
        "default_threshold": 95,
        "purpose": "Classify user intent or problem type into structured JSON with intent, confidence, and reasoning.",
        "metrics": [
            ("board_accuracy", "25%", "1.0 if predicted `intent` equals expected `intent` (case-insensitive); else 0.0"),
            ("subject_accuracy", "25%", "Same as intent match (routing proxy metric)"),
            ("topic_accuracy", "20%", "1.0 if `confidence` >= `confidence_min` in expected (default 0.5); else 0.5"),
            ("intent_accuracy", "20%", "Exact match on `intent` field between model output and reference"),
            ("schema_validity", "10%", "1.0 if JSON output contains keys: `intent`, `confidence`, `reasoning`"),
        ],
        "pass_rule": "weighted_score >= passing_threshold AND intent_accuracy = 1.0 for strict routing cases",
        "fail_examples": [
            "Wrong intent slug (e.g. `question` instead of `definition`)",
            "Missing JSON keys (`intent`, `confidence`, `reasoning`)",
            "Confidence below minimum when intent is otherwise correct",
        ],
    },
    "query_rewriter": {
        "class": "QueryRewriterEvaluator",
        "default_threshold": 90,
        "purpose": "Measure whether rewritten search queries preserve user intent and improve vector retrieval recall.",
        "metrics": [
            ("retrieval_recall_improvement", "40%", "Set overlap: |predicted queries ∩ expected queries| / |expected queries| (lowercased)"),
            ("query_relevance", "30%", "Same overlap ratio as recall — queries must match gold paraphrases"),
            ("conciseness", "10%", "1.0 if average query length is 3–25 words; else 0.5"),
            ("searchability", "20%", "1.0 if at least one non-empty query returned; else 0.0"),
        ],
        "pass_rule": "weighted_score >= passing_threshold with high query overlap and non-empty queries array",
        "fail_examples": [
            "Empty `queries` array",
            "Queries drift to unrelated topic",
            "No overlap with expected retrieval strings",
            "Queries too long (>25 words average) or too short (<3 words)",
        ],
    },
    "verifier": {
        "class": "VerifierEvaluator",
        "default_threshold": 95,
        "purpose": "Ensure hallucinated or unsupported sentences are removed or softened in corrected answers.",
        "metrics": [
            ("hallucination_detection", "40%", "1.0 if none of `unsupported_sentences` appear in corrected output; penalized per leak"),
            ("false_positive_control", "20%", "1.0 unless answer wrongly labels general knowledge when not allowed"),
            ("source_alignment", "25%", "Same as hallucination detection — stay within context vocabulary"),
            ("correction_quality", "15%", "Same as hallucination detection — unsupported claims removed"),
        ],
        "pass_rule": "weighted_score >= passing_threshold AND zero unsupported sentences leaked into output",
        "fail_examples": [
            "Unsupported fact still present in corrected answer",
            "Invented numbers/names not in context excerpt",
        ],
    },
    "formatter": {
        "class": "FormatterEvaluator",
        "default_threshold": 98,
        "purpose": "Validate structured output format — JSON schema compliance, markdown structure, consistency.",
        "metrics": [
            ("schema_compliance", "50%", "If `quiz_json`/`json_output`/`flashcards_json` etc. expected: 1.0 if output parses as valid JSON; else 0.0. Otherwise 1.0"),
            ("format_quality", "30%", "1.0 if markdown headings (`#`), bullets (`-`), numbered lists, OR valid JSON present; else 0.5"),
            ("consistency", "20%", "Same as format_quality — stable structure across output"),
        ],
        "pass_rule": "weighted_score >= passing_threshold; JSON agents require parseable JSON for schema_compliance=1.0",
        "fail_examples": [
            "Invalid JSON when JSON output required",
            "No markdown structure for text outputs",
            "Markdown fences wrapping JSON body",
        ],
    },
    "hint_agent": {
        "class": "HintAgentEvaluator",
        "default_threshold": 90,
        "purpose": "Guided tutoring without leaking final answer too early; progressive hints with structured coach JSON.",
        "metrics": [
            ("helpfulness", "35%", "1.0 if `sections` or `title` present in coach JSON; else 0.6"),
            ("progressive_guidance", "25%", "1.0 if `revealLevel` is `hint`, `partial`, or empty; else 0.8"),
            ("answer_leakage_control", "25%", "0.0 if `no_final_answer` expected but `finalAnswer` is non-empty; else 1.0"),
            ("clarity", "15%", "1.0 if structured sections or title present; else 0.6"),
        ],
        "pass_rule": "weighted_score >= passing_threshold; early interactions must not leak `finalAnswer` when expected",
        "fail_examples": [
            "Final numeric answer revealed at interaction_count=0",
            "Missing `sections` or coach structure",
            "revealLevel=`full` when hint-only expected",
        ],
    },
    "retriever": {
        "class": "RetrieverEvaluator",
        "default_threshold": 90,
        "purpose": "Check retrieved context contains expected phrases from source documents.",
        "metrics": [
            ("context_recall", "40%", "Count of expected_phrases found in context / total phrases"),
            ("context_precision", "30%", "Same as recall"),
            ("top_k_accuracy", "20%", "Same as recall"),
            ("ranking_quality", "10%", "Same as recall"),
        ],
        "pass_rule": "weighted_score >= passing_threshold with high phrase recall in retrieved context",
        "fail_examples": ["Expected phrases missing from retrieved context"],
    },
    "answer_generator": {
        "class": "AnswerGeneratorEvaluator",
        "default_threshold": 90,
        "purpose": "Judge RAG answer quality via LLM-as-judge on accuracy, completeness, grounding, exam-worthiness.",
        "metrics": [
            ("accuracy", "40%", "LLM judge score 1–5 normalized to 0–1"),
            ("completeness", "25%", "LLM judge — answer covers the question"),
            ("source_grounding", "20%", "LLM judge — answer supported by context excerpts"),
            ("exam_worthiness", "15%", "LLM judge — suitable for CBSE/NCERT exam prep"),
        ],
        "pass_rule": "weighted_score >= passing_threshold based on LLM judge dimensions",
        "fail_examples": ["Unsupported claims", "Incomplete answer", "Off-topic response"],
    },
}

AGENT_SPECIFIC: Dict[str, Dict[str, str]] = {
    "intent_classifier": {
        "role": "Routes user messages to the correct RAG pipeline (retrieval, summary, security block, creation, etc.).",
        "evaluates": "Exact intent slug from 13 allowed values; security/jailbreak detection; confidence calibration; JSON schema.",
        "key_outputs": "`intent`, `confidence`, `reasoning`",
    },
    "query_rewriter": {
        "role": "Rewrites user queries into search-optimized strings for vector/hybrid retrieval.",
        "evaluates": "Query paraphrase overlap with gold queries; intent preservation; conciseness; non-empty output.",
        "key_outputs": "`queries[]`, `confidence`, `reasoning`",
    },
    "query_decomposer": {
        "role": "Splits multi-part user questions into independent sub-queries for retrieval.",
        "evaluates": "Sub-query set overlap; each sub-query searchable; intent preserved across parts.",
        "key_outputs": "`queries[]` array of sub-queries",
    },
    "scope_narrower": {
        "role": "Narrows retrieval scope (whole document vs section vs chapter).",
        "evaluates": "Scoped query strings match expected narrowed search phrases.",
        "key_outputs": "`queries[]` with document scope applied",
    },
    "chat_policy_block": {
        "role": "Applies chat policy YAML rules to user messages.",
        "evaluates": "Structured policy response; format compliance; policy fields present.",
        "key_outputs": "`policy_applied`, `response_hint`",
    },
    "direct_chat": {
        "role": "Direct conversational responses without RAG retrieval.",
        "evaluates": "Readable markdown or plain text; coherent structure; format quality.",
        "key_outputs": "`output` text/markdown",
    },
    "chat_summarizer": {
        "role": "Summarizes chat transcripts at requested scope.",
        "evaluates": "Summary markdown structure (headings/bullets); concise format.",
        "key_outputs": "`summary_markdown`",
    },
    "hallucination_guard_retry": {
        "role": "Removes or softens unsupported sentences from draft answers using context evidence.",
        "evaluates": "Zero leakage of unsupported sentences; source-aligned corrections.",
        "key_outputs": "`corrected_answer`",
    },
    "studio_system_json": {
        "role": "Studio base system prompt for JSON/markdown educational artifact generation.",
        "evaluates": "Valid JSON or markdown output per task type.",
        "key_outputs": "`json_output`",
    },
    "studio_quiz": {
        "role": "Generates MCQ quiz JSON from source material.",
        "evaluates": "Valid parseable quiz JSON; 4 options per question; schema_compliance critical.",
        "key_outputs": "`quiz_json` with title, questions[], correct_answer, explanation",
    },
    "studio_flashcards": {
        "role": "Generates flashcard deck JSON from source material.",
        "evaluates": "Valid flashcards JSON structure; front/back pairs.",
        "key_outputs": "`flashcards_json`",
    },
    "studio_mind_map": {
        "role": "Generates mind map JSON hierarchy from source material.",
        "evaluates": "Valid mind map JSON; nested node structure.",
        "key_outputs": "`mind_map_json`",
    },
    "studio_slide_deck": {
        "role": "Generates slide deck JSON from source material.",
        "evaluates": "Valid slide deck JSON; slides array with titles and bullets.",
        "key_outputs": "`slide_deck_json`",
    },
    "studio_fallback_legacy": {
        "role": "Legacy fallback studio task prompt for unspecified artifact types.",
        "evaluates": "Format compliance for generated educational content.",
        "key_outputs": "`output`",
    },
    "studio_context_embedding_query": {
        "role": "Builds embedding search query for studio context retrieval.",
        "evaluates": "Structured embedding query string; format compliance.",
        "key_outputs": "`embedding_query`",
    },
    "problem_dna_analyzer": {
        "role": "Classifies problem type to route to the correct problem-solving coach.",
        "evaluates": "Problem classification intent match; JSON schema; confidence.",
        "key_outputs": "`intent`, `confidence`, `reasoning` (problem type)",
    },
    "explain_from_basics": {
        "role": "Coaches student by explaining concepts from fundamentals without giving final answer early.",
        "evaluates": "Coach JSON structure; no answer leakage; progressive hints; sections present.",
        "key_outputs": "`coach_json` with sections, revealLevel",
    },
    "show_best_approach": {
        "role": "Reveals the optimal solution approach for a problem.",
        "evaluates": "Coach structure; method explanation; leakage control per interaction_count.",
        "key_outputs": "`coach_json`",
    },
    "show_missing_idea": {
        "role": "Identifies the missing concept in student's reasoning.",
        "evaluates": "Gap identification in coach JSON; structured sections; no premature final answer.",
        "key_outputs": "`coach_json`",
    },
    "help_me_solve_it": {
        "role": "Socratic guided solving with checkpoint MCQs; no final answer until ready.",
        "evaluates": "Checkpoint MCQ structure; hint-level revealLevel; sections; leakage control at interaction_count=0.",
        "key_outputs": "`coach_json` with checkpoint, sections, revealLevel",
    },
    "problem_solver_followup": {
        "role": "Handles follow-up button actions (next hint, reveal solution, similar problem).",
        "evaluates": "Follow-up coach JSON; appropriate revealLevel for action type.",
        "key_outputs": "`coach_json`",
    },
    "tutor_notebook_bootstrap": {
        "role": "Creates initial tutor notebook learning path from source summaries.",
        "evaluates": "Bootstrap JSON/markdown structure; format compliance.",
        "key_outputs": "`bootstrap_json`",
    },
    "tutor_follow_up_questions": {
        "role": "Generates 2–4 follow-up questions after a tutor answer.",
        "evaluates": "Valid JSON array or markdown list of questions; format structure.",
        "key_outputs": "`follow_up_questions[]`",
    },
    "source_question_extraction": {
        "role": "Extracts MCQ/numerical questions from uploaded document excerpts.",
        "evaluates": "Valid questions JSON; structured extraction output.",
        "key_outputs": "`questions_json`",
    },
    "document_sketch": {
        "role": "Creates high-level document outline/sketch from raw text sample.",
        "evaluates": "Sketch JSON structure; format compliance.",
        "key_outputs": "`sketch_json`",
    },
    "ncert_document_sketch": {
        "role": "NCERT-specific document sketch with chapter structure.",
        "evaluates": "NCERT-aligned sketch JSON; format compliance.",
        "key_outputs": "`sketch_json`",
    },
    "chunk_contextualization": {
        "role": "Adds surrounding document context to an isolated chunk for better retrieval.",
        "evaluates": "Contextualized chunk text structure; format quality.",
        "key_outputs": "`contextualized_chunk`",
    },
    "whole_file_map_summarizer": {
        "role": "Map-phase summarizer for whole-file processing (per section).",
        "evaluates": "Section summary format; markdown/JSON structure.",
        "key_outputs": "`section_summary`",
    },
    "whole_file_reduce": {
        "role": "Reduce-phase aggregator combining section summaries into final answer.",
        "evaluates": "Final answer format; coherent structured output.",
        "key_outputs": "`final_answer`",
    },
    "whole_file_map_template": {
        "role": "Template for map-phase summaries across document excerpts.",
        "evaluates": "Map summaries JSON structure; format compliance.",
        "key_outputs": "`map_summaries`",
    },
    "image_ocr": {
        "role": "Extracts text from uploaded image fixtures (OCR simulation).",
        "evaluates": "Extracted text format; readable output structure.",
        "key_outputs": "`extracted_text`",
    },
    "diagram_label_ocr": {
        "role": "Extracts diagram labels from image fixtures.",
        "evaluates": "Labels text format; structured label extraction.",
        "key_outputs": "`labels_text`",
    },
    "refusal_templates": {
        "role": "Generates policy-compliant refusal messages for guardrail scenarios.",
        "evaluates": "Refusal JSON with reason + user-facing message; format compliance.",
        "key_outputs": "`refusal_reason`, `user_facing_message`",
    },
}


def _load_dataset(agent_id: str, path: str) -> dict:
    p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _variations(items: list) -> str:
    c = Counter(str(it.get("variation", "")) for it in items)
    return ", ".join(f"`{k}` ({v})" for k, v in sorted(c.items()) if k)


def _item_evaluators(items: list) -> str:
    evs: set = set()
    for it in items:
        for e in it.get("evaluators") or []:
            evs.add(str(e))
    return ", ".join(f"`{e}`" for e in sorted(evs)) or "n/a"


def _example_block(items: list) -> str:
    if not items:
        return "*No examples in dataset.*"
    ex = items[0]
    inp = json.dumps(ex.get("inputs") or {}, indent=2)
    out = json.dumps(ex.get("reference_outputs") or {}, indent=2)
    if len(inp) > 800:
        inp = inp[:800] + "\n  ..."
    if len(out) > 800:
        out = out[:800] + "\n  ..."
    return f"""**Example ID:** `{ex.get('id', 'n/a')}` | **Variation:** `{ex.get('variation', '')}` | **Tags:** {', '.join(ex.get('tags') or [])}

**Input:**
```json
{inp}
```

**Reference output (gold label):**
```json
{out}
```"""


def _agent_section(ds: dict, cfg: dict, doc: dict) -> str:
    aid = ds["dataset_id"]
    sno = ds.get("sno", "?")
    name = ds.get("agent_name", aid)
    category = ds.get("category_folder", "")
    tier = ds.get("tier", "")
    count = ds.get("actual_examples", 0)
    acfg = cfg.get("agents", {}).get(aid) or {}
    evaluator = acfg.get("evaluator", "formatter")
    threshold = acfg.get("passing_threshold", EVALUATOR_METRICS.get(evaluator, {}).get("default_threshold", 90))
    models = acfg.get("models") or ["gpt-4o-mini"]
    prompts = acfg.get("prompt_versions") or ["v1"]
    ev_info = EVALUATOR_METRICS.get(evaluator, EVALUATOR_METRICS["formatter"])
    spec = AGENT_SPECIFIC.get(aid, {"role": name, "evaluates": ev_info["purpose"], "key_outputs": "see dataset"})
    langsmith = doc.get("langsmith") or {}
    input_keys = langsmith.get("input_keys") or []
    output_keys = langsmith.get("output_keys") or []
    items = doc.get("items") or []

    metrics_rows = "\n".join(
        f"| `{m[0]}` | {m[1]} | {m[2]} |" for m in ev_info["metrics"]
    )
    fail_rows = "\n".join(f"- {f}" for f in ev_info["fail_examples"])

    return f"""## Agent {sno}: `{aid}` — {name}

### A. Agent overview

| Field | Value |
|-------|-------|
| **S.no** | {sno} |
| **Agent ID** | `{aid}` |
| **Display name** | {name} |
| **Category** | {category} |
| **Tier** | {tier} ({count} examples) |
| **Role** | {spec['role']} |

### B. Dataset used

| Field | Value |
|-------|-------|
| **Local path** | `{ds.get('path', '')}` |
| **LangSmith dataset** | `nbm-prompt-{aid}` |
| **Example count** | {count} |
| **Variations in dataset** | {_variations(items)} |
| **Item-level annotations** | {_item_evaluators(items)} |

### C. Input / output contract

| Direction | Keys |
|-----------|------|
| **Inputs** | {', '.join(f'`{k}`' for k in input_keys) or 'see dataset JSON'} |
| **Reference outputs (gold)** | {', '.join(f'`{k}`' for k in output_keys) or 'see dataset JSON'} |
| **Key outputs evaluated** | {spec.get('key_outputs', '')} |

### D. Evaluator assigned to this agent

| Field | Value |
|-------|-------|
| **Runtime evaluator** | `{evaluator}` |
| **Evaluator class** | `{ev_info['class']}` |
| **Pass threshold** | **{threshold}%** |
| **Prompt versions tested** | {', '.join(f'`{p}`' for p in prompts)} |
| **Models tested** | {', '.join(f'`{m}`' for m in models)} |

### E. Evaluation criteria (detailed scoring for this agent)

**What this agent is evaluated on:** {spec['evaluates']}

**Scoring formula:**
```
weighted_score = (Σ metric_i × weight_i) / (Σ weight_i) × 100
PASS if weighted_score >= {threshold}
FAIL if weighted_score < {threshold}
```

| Metric | Weight | How it is scored for `{aid}` |
|--------|--------|------------------------------|
{metrics_rows}

**Pass rule for this agent:** {ev_info['pass_rule']} (threshold = {threshold}%)

**Common failure modes for this agent:**
{fail_rows}

### F. Worked example from dataset

{_example_block(items)}

### G. LangSmith verification

- **Dataset:** Datasets & Experiments → `nbm-prompt-{aid}`
- **Eval runs:** Tracing → `eval/{aid}/{{example_id}}`
- **Experiment summary:** Tracing → `experiment/{aid}/{{prompt}}/{{model}}`
- **Feedback keys:** `weighted_score`, `passed`, `metric_*`, `total_cost_usd`

---

"""


def generate() -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cfg = yaml.safe_load(MODELS.read_text(encoding="utf-8")) or {}
    datasets = sorted(manifest.get("datasets") or [], key=lambda d: d.get("sno", 0))

    lines = [
        "# Per-agent evaluation criteria (all 33 agents)",
        "",
        "Each agent below has its **own dedicated** evaluation criteria — dataset, scorer, metrics, weights, pass/fail rules, and example.",
        "Do not edit manually. Regenerate: `python scripts/generate_agent_eval_criteria_sections.py`",
        "",
        "**Formula (all agents):** `weighted_score = (Σ metric × weight) / (Σ weight) × 100`",
        "",
    ]
    for ds in datasets:
        doc = _load_dataset(ds["dataset_id"], ds["path"])
        lines.append(_agent_section(ds, cfg, doc))

    lines.append(f"*Total agents documented: {len(datasets)}*")
    return "\n".join(lines)


def merge_into_main(body: str) -> None:
    if not MAIN.is_file():
        MAIN.write_text(body, encoding="utf-8")
        return
    text = MAIN.read_text(encoding="utf-8")
    block = f"{START}\n{body}\n{END}"
    if START in text and END in text:
        pre = text[: text.index(START)]
        post = text[text.index(END) + len(END) :]
        text = pre + block + post
    else:
        # Insert before comparison appendix if present
        marker = "<!-- COMPARISON_APPENDIX_START -->"
        if marker in text:
            pre = text[: text.index(marker)]
            post = text[text.index(marker) :]
            text = pre.rstrip() + "\n\n" + block + "\n\n" + post
        else:
            text = text.rstrip() + "\n\n" + block
    MAIN.write_text(text, encoding="utf-8")


def main() -> int:
    body = generate()
    OUT.write_text(body, encoding="utf-8")
    merge_into_main(body)
    print(f"Wrote {OUT} ({body.count('## Agent')} agent sections)")
    print(f"Merged into {MAIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
