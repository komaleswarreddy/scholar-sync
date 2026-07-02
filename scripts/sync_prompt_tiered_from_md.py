#!/usr/bin/env python3
"""Emit evals/datasets/prompt_tiered/*.json from Complete_Agent_DataSet.md.

The markdown file is the source of truth. This script parses each agent section,
extracts metadata, evaluation examples (inputs, reference outputs, evaluators),
and writes LangSmith-compatible dataset JSON plus an updated manifest.json.

Usage:
    python scripts/sync_prompt_tiered_from_md.py                  # all agents
    python scripts/sync_prompt_tiered_from_md.py document_sketch  # one slug
    python scripts/sync_prompt_tiered_from_md.py --batch 26-30    # sno range
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
OUTPUT_DIR = ROOT / "evals" / "datasets" / "prompt_tiered"

SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)
EXAMPLE_RE_V2 = re.compile(r"^####\s+Example\b.*?:\s*`([^`]+)`", re.M)
EXAMPLE_RE_LEGACY = re.compile(r"^####\s+Example\s+\d+:\s+(\S+)\s*$", re.M)
FIELD_RE = re.compile(r"^\*\*([^*]+):\*\*(.*)$")

SNO_TO_SLUG: dict[int, str] = {
    1: "intent_classifier",
    2: "query_rewriter",
    3: "query_decomposer",
    4: "scope_narrower",
    5: "chat_policy_block",
    6: "direct_chat",
    7: "rag_chat_response_generator",
    8: "chat_summarizer",
    9: "hallucination_guard_retry",
    10: "studio_system_json",
    11: "studio_quiz",
    12: "studio_flashcards",
    13: "studio_mind_map",
    14: "studio_slide_deck",
    15: "studio_fallback_legacy",
    16: "studio_context_embedding_query",
    17: "problem_dna_analyzer",
    18: "explain_from_basics",
    19: "show_best_approach",
    20: "show_missing_idea",
    21: "help_me_solve_it",
    22: "problem_solver_followup",
    23: "tutor_notebook_bootstrap",
    24: "tutor_follow_up_questions",
    25: "source_question_extraction",
    26: "document_sketch",
    27: "ncert_document_sketch",
    28: "chunk_contextualization",
    29: "whole_file_map_summarizer",
    30: "whole_file_reduce",
    32: "image_ocr",
    33: "diagram_label_ocr",
    34: "refusal_templates",
    35: "orchestration_flow",
}

SLUG_TO_FOLDER: dict[str, str] = {
    "intent_classifier": "routing",
    "query_rewriter": "retrieval",
    "query_decomposer": "retrieval",
    "scope_narrower": "retrieval",
    "chat_policy_block": "generation",
    "direct_chat": "generation",
    "rag_chat_response_generator": "generation",
    "chat_summarizer": "generation",
    "hallucination_guard_retry": "generation",
    "studio_system_json": "studio",
    "studio_quiz": "studio",
    "studio_flashcards": "studio",
    "studio_mind_map": "studio",
    "studio_slide_deck": "studio",
    "studio_fallback_legacy": "studio",
    "studio_context_embedding_query": "studio",
    "problem_dna_analyzer": "problem_solving",
    "explain_from_basics": "problem_solving",
    "show_best_approach": "problem_solving",
    "show_missing_idea": "problem_solving",
    "help_me_solve_it": "problem_solving",
    "problem_solver_followup": "problem_solving",
    "tutor_notebook_bootstrap": "tutor_mode",
    "tutor_follow_up_questions": "tutor_mode",
    "source_question_extraction": "source_upload",
    "document_sketch": "source_upload",
    "ncert_document_sketch": "source_upload",
    "chunk_contextualization": "source_upload",
    "whole_file_map_summarizer": "source_upload",
    "whole_file_reduce": "source_upload",
    "image_ocr": "source_upload",
    "diagram_label_ocr": "source_upload",
    "refusal_templates": "safety",
    "orchestration_flow": "orchestration",
}

# Output fields whose fenced JSON body is nested under the key name.
NESTED_JSON_OUTPUT_KEYS = {
    "sketch_json",
    "dna_json",
    "coach_json",
    "bootstrap_json",
    "contextualization_json",
    "quiz_json",
    "json_output",
    "sections_json",
}

INT_KEYS = {
    "class_num",
    "page_number",
    "figure_index",
    "max_rewrites",
    "max_chunks",
    "interaction_count",
    "chapter_no",
    "target_context_tokens",
    "target_summary_tokens",
    "target_concept_terms",
    "selected_source_count",
    "source_count",
}

FLOAT_KEYS = {"confidence"}

BOOL_KEYS = {"requires_retrieval", "requires_attachment", "passes_policy"}


def label_to_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")


def parse_scalar(key: str, raw: str) -> Any:
    text = raw.strip()
    if text.lower() == "null":
        return None
    if key in BOOL_KEYS:
        return text.lower() == "true"
    if key in INT_KEYS:
        try:
            return int(text)
        except ValueError:
            return text
    if key in FLOAT_KEYS:
        try:
            return float(text)
        except ValueError:
            return text
    return text


def parse_block_body(body: str) -> Any:
    body = body.strip("\n")
    if not body:
        return ""
    fence = re.match(r"```(\w+)?\s*\n(.*)\n```\s*$", body, re.S)
    if fence:
        lang = (fence.group(1) or "").lower()
        inner = fence.group(2)
        if lang == "json" or inner.lstrip().startswith(("{", "[")):
            return json.loads(inner)
        return inner
    lines = body.splitlines()
    if lines and all(ln.strip().startswith("- ") for ln in lines if ln.strip()):
        return [ln.strip()[2:].strip() for ln in lines if ln.strip()]
    return body


def parse_fields(region: str) -> dict[str, Any]:
    """Parse **Label:** fields from an Inputs or Expected output region."""
    fields: dict[str, Any] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is None:
            return
        body = "\n".join(current_lines).strip()
        if body and not body.startswith("\n") and "\n" not in body and not body.startswith("```"):
            fields[current_key] = parse_scalar(current_key, body)
        else:
            fields[current_key] = parse_block_body(body) if body else ""
        current_key = None
        current_lines = []

    for line in region.splitlines():
        m = FIELD_RE.match(line)
        if m:
            flush()
            key = label_to_key(m.group(1))
            rest = m.group(2)
            if rest.strip():
                if rest.strip().startswith("- "):
                    fields[key] = parse_block_body(rest.strip())
                else:
                    fields[key] = parse_scalar(key, rest)
                current_key = None
                current_lines = []
            else:
                current_key = key
                current_lines = []
        elif current_key is not None:
            current_lines.append(line)
    flush()
    return fields


def split_region(block: str, start_marker: str, end_markers: list[str]) -> str:
    idx = block.find(start_marker)
    if idx == -1:
        return ""
    start = idx + len(start_marker)
    rest = block[start:]
    end = len(rest)
    for marker in end_markers:
        pos = rest.find(marker)
        if pos != -1:
            end = min(end, pos)
    return rest[:end]


def parse_evaluators(block: str) -> list[str]:
    m = re.search(r"^\*\*Evaluators:\*\*\s*(.+)$", block, re.M)
    if m:
        return [e.strip() for e in m.group(1).split(",") if e.strip()]
    m = re.search(r"^\*\*Quality Check:\*\*\s*(.+)$", block, re.M)
    if not m:
        return []
    dims: list[str] = []
    for part in re.split(r"\.\s+", m.group(1)):
        part = part.strip().rstrip(".")
        if not part:
            continue
        name = part.split(":", 1)[0].strip()
        if name and name.lower() not in ("n/a", "pass", "fail"):
            if re.match(r"^[a-z][a-z0-9_]*$", name):
                dims.append(name)
    return dims


def parse_variation_and_tags(block: str) -> tuple[str, list[str]]:
    variation = ""
    tags: list[str] = []
    mv = re.search(r"(?:^-\s+)?\*\*Variation:\*\*\s*(.+)$", block, re.M)
    if mv:
        variation = mv.group(1).strip().strip("`")
    mt = re.search(r"-\s+\*\*Tags:\*\*\s*(.+)$", block, re.M)
    if mt:
        tags = [t.strip() for t in mt.group(1).split(",") if t.strip()]
    return variation, tags


def build_reference_outputs(fields: dict[str, Any], output_keys: list[str]) -> dict[str, Any]:
    ref: dict[str, Any] = {}
    for key, value in fields.items():
        if key == "refusal_json" and isinstance(value, dict):
            ref.update(value)
            continue
        if key in NESTED_JSON_OUTPUT_KEYS:
            ref[key] = value
            continue
        if key in output_keys or not output_keys:
            ref[key] = value
    if output_keys:
        return {k: ref[k] for k in output_keys if k in ref}
    return ref


def split_examples(section: str) -> list[tuple[str, str]]:
    hits = list(EXAMPLE_RE_V2.finditer(section))
    if not hits:
        hits = list(EXAMPLE_RE_LEGACY.finditer(section))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(hits):
        ex_id = m.group(1).strip()
        start = m.start()
        end = hits[i + 1].start() if i + 1 < len(hits) else len(section)
        out.append((ex_id, section[start:end]))
    return out


def parse_metadata_table(section: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", section, re.M):
        key = m.group(1).strip()
        val = m.group(2).strip().strip("`")
        if key.lower() not in ("field", "-------"):
            rows[key] = val
    return rows


def parse_langsmith_keys(section: str) -> tuple[list[str], list[str]]:
    input_keys: list[str] = []
    output_keys: list[str] = []
    in_langsmith = False
    for line in section.splitlines():
        if line.startswith("**LangSmith configuration**"):
            in_langsmith = True
            continue
        if in_langsmith and line.startswith("**") and "LangSmith" not in line:
            in_langsmith = False
        if not in_langsmith:
            continue
        if "Input keys:" in line:
            raw = line.split("Input keys:", 1)[1].strip()
            input_keys = re.findall(r"`([^`]+)`", raw)
        if "Output keys:" in line:
            raw = line.split("Output keys:", 1)[1].strip()
            output_keys = re.findall(r"`([^`]+)`", raw)
    return input_keys, output_keys


def extract_prompt_template(section: str) -> str:
    markers = [
        "**Prompt template (production):**",
        "**Prompt template:**",
    ]
    start = -1
    for marker in markers:
        pos = section.find(marker)
        if pos != -1:
            start = pos + len(marker)
            break
    if start == -1:
        return ""
    rest = section[start:]
    end = rest.find("### Evaluation examples")
    if end == -1:
        end = len(rest)
    text = rest[:end].strip()
    fence = re.match(r"```(?:\w+)?\s*\n(.*)\n```", text, re.S)
    if fence:
        return fence.group(1).strip()
    return text.strip()


def parse_example_block(block: str, output_keys: list[str]) -> dict[str, Any]:
    variation, tags = parse_variation_and_tags(block)
    inputs_region = split_region(
        block,
        "**Inputs**",
        ["**Expected output**", "Expected output", "**Quality Check:**", "---"],
    )
    if not inputs_region.strip():
        inputs_region = split_region(
            block,
            "Inputs\n",
            ["Expected output", "**Quality Check:**", "---"],
        )
    outputs_region = split_region(
        block,
        "**Expected output**",
        ["**Quality Check:**", "**Evaluators:**", "---"],
    )
    if not outputs_region.strip():
        outputs_region = split_region(
            block,
            "Expected output\n",
            ["**Quality Check:**", "**Evaluators:**", "---"],
        )

    inputs = parse_fields(inputs_region)
    output_fields = parse_fields(outputs_region)
    reference_outputs = build_reference_outputs(output_fields, output_keys)
    evaluators = parse_evaluators(block)

    item: dict[str, Any] = {
        "variation": variation,
        "inputs": inputs,
        "reference_outputs": reference_outputs,
    }
    if tags:
        item["tags"] = tags
    if evaluators:
        item["evaluators"] = evaluators
    return item


def tier_to_slug(tier: str) -> str:
    m = re.search(r"(\d+)", tier)
    return f"tier_{m.group(1)}" if m else "tier_3"


def build_dataset(slug: str, sno: int, section: str) -> dict[str, Any]:
    meta = parse_metadata_table(section)
    input_keys, output_keys = parse_langsmith_keys(section)
    examples = split_examples(section)
    items: list[dict[str, Any]] = []
    for ex_id, block in examples:
        parsed = parse_example_block(block, output_keys)
        row: dict[str, Any] = {
            "id": ex_id,
            "variation": parsed["variation"],
            "inputs": parsed["inputs"],
            "reference_outputs": parsed["reference_outputs"],
        }
        if parsed.get("tags"):
            row["tags"] = parsed["tags"]
        if parsed.get("evaluators"):
            row["evaluators"] = parsed["evaluators"]
        items.append(row)

    agent_name = re.sub(r"^\d+\.\s+", "", SECTION_RE.search(section).group(2)) if SECTION_RE.search(section) else slug
    return {
        "version": meta.get("Version", "1.0.0"),
        "dataset_id": slug,
        "agent": {
            "sno": sno,
            "category": meta.get("Category", ""),
            "name": agent_name,
            "tier": tier_to_slug(meta.get("Tier", "Tier 3")),
            "target_examples": int(meta.get("Target examples", len(items))),
            "prompt_template": extract_prompt_template(section),
        },
        "langsmith": {
            "dataset_name_prefix": "nbm-prompt",
            "input_keys": input_keys,
            "output_keys": output_keys,
        },
        "items": items,
    }


def write_dataset(slug: str, payload: dict[str, Any]) -> Path:
    folder = SLUG_TO_FOLDER[slug]
    out_dir = OUTPUT_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.json"
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


def parse_batch_arg(arg: str) -> tuple[int, int] | None:
    m = re.match(r"^(\d+)-(\d+)$", arg.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def main() -> int:
    batch: tuple[int, int] | None = None
    target_slug: str | None = None
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--batch" and i + 1 < len(argv):
            batch = parse_batch_arg(argv[i + 1])
            i += 2
            continue
        if arg.startswith("--batch="):
            batch = parse_batch_arg(arg.split("=", 1)[1])
            i += 1
            continue
        target_slug = arg
        i += 1
    sections = {}
    text = MD_PATH.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        sno = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[sno] = text[start:end]

    manifest_entries: list[dict[str, Any]] = []
    total_items = 0
    errors: list[str] = []

    for sno, slug in sorted(SNO_TO_SLUG.items()):
        if target_slug and slug != target_slug:
            continue
        if batch and not (batch[0] <= sno <= batch[1]):
            continue
        if sno not in sections:
            errors.append(f"{slug}: MD section ## {sno}. missing")
            continue
        payload = build_dataset(slug, sno, sections[sno])
        if not payload["items"]:
            errors.append(f"{slug}: no examples parsed")
        path = write_dataset(slug, payload)
        rel = path.relative_to(ROOT).as_posix()
        count = len(payload["items"])
        total_items += count
        manifest_entries.append({
            "dataset_id": slug,
            "path": rel,
            "tier": payload["agent"]["tier"],
            "target_examples": payload["agent"]["target_examples"],
            "actual_examples": count,
            "category_folder": SLUG_TO_FOLDER[slug],
            "agent_name": payload["agent"]["name"],
            "sno": sno,
        })
        print(f"  [{payload['agent']['tier']}] {slug}: {count} items -> {rel}")

    if not batch and not target_slug:
        manifest = {
            "version": "1.4.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "scripts/sync_prompt_tiered_from_md.py",
            "source_of_truth": "Reference dataset/Complete_Agent_DataSet.md",
            "skipped_agents": [
                "whole_file_map_template (S.no 31)",
            ],
            "tier_counts": {
                "tier_1": sum(1 for e in manifest_entries if e["tier"] == "tier_1"),
                "tier_2": sum(1 for e in manifest_entries if e["tier"] == "tier_2"),
                "tier_3": sum(1 for e in manifest_entries if e["tier"] == "tier_3"),
            },
            "total_datasets": len(manifest_entries),
            "total_items": total_items,
            "datasets": manifest_entries,
        }
        manifest_path = OUTPUT_DIR / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote manifest: {manifest_path.relative_to(ROOT).as_posix()}")
        print(f"Summary: {len(manifest_entries)} datasets, {total_items} total items")

    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    print(f"Syncing prompt_tiered datasets from {MD_PATH.name}")
    sys.exit(main())
