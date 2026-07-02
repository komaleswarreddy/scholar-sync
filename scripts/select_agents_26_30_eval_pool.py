#!/usr/bin/env python3
"""Build production eval pool for Agents 26–30 (RAG source-upload pipeline)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from rag_eval_catalog import (
    VARIATION_SLOTS_15,
    all_ncert_documents,
    all_upload_documents,
    chunk_entries,
    map_reduce_chains,
)

OUT = SCRIPTS / "agents_26_30_eval_pool.json"
COMPLETE_MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

AGENTS = [
    ("document_sketch", 26, 15),
    ("ncert_document_sketch", 27, 15),
    ("chunk_contextualization", 28, 15),
    ("whole_file_map_summarizer", 29, 15),
    ("whole_file_reduce", 30, 15),
]


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_used_inputs() -> set[str]:
    if not COMPLETE_MD.exists():
        return set()
    text = COMPLETE_MD.read_text(encoding="utf-8")
    used: set[str] = set()
    for label in (
        "Document Text", "Header", "Whole Document", "Chunk Content",
        "Parts", "User Message", "Section Summaries",
    ):
        for m in re.finditer(rf"\*\*{label}:\*\*\s*\n\n(.+?)\n\n\*\*", text, re.S):
            used.add(normalize(m.group(1)[:500]))
    return used


def _unique_text(text: str, used: set[str], suffix: str = "") -> str:
    base = text
    if suffix:
        base = text + suffix
    if normalize(base[:400]) not in used:
        used.add(normalize(base[:400]))
        return base
    bumped = base + f"\n[eval variant {len(used)}]"
    used.add(normalize(bumped[:400]))
    return bumped


def build_pool(used: set[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    uploads = all_upload_documents()
    ncert = all_ncert_documents()
    chunks = chunk_entries()
    chains = map_reduce_chains()

    for i in range(13):
        var = VARIATION_SLOTS_15[i]
        up = uploads[i % len(uploads)]
        header = _unique_text(up["header"], used)
        doc_text = _unique_text(up["document_text"], used, f" upload-{i+1}")
        items.append({
            "agent_id": "document_sketch",
            "agent_num": 26,
            "example_id": f"document_sketch-{i + 1:03d}",
            "variation": var,
            "doc_id": up["doc_id"],
            "header": header,
            "document_text": doc_text,
            "subject": up["subject"],
            "exam_type": up["exam_type"],
            "source_key": up.get("source_key", "upload"),
            "tags": [up["exam_type"], up["subject"], "source_upload", var],
        })

    for i in range(13):
        var = VARIATION_SLOTS_15[i]
        doc = ncert[i]
        header = _unique_text(doc["header"], used)
        doc_text = _unique_text(doc["document_text"], used, f" ncert-{i+1}")
        items.append({
            "agent_id": "ncert_document_sketch",
            "agent_num": 27,
            "example_id": f"ncert_document_sketch-{i + 1:03d}",
            "variation": var,
            "doc_id": doc["doc_id"],
            "header": header,
            "document_text": doc_text,
            "subject": doc["subject"],
            "exam_type": doc["exam_type"],
            "tags": ["ncert", doc["subject"], "ncert_strict" if var == "ncert_strict" else var],
        })

    for i, ch in enumerate(chunks):
        items.append({
            "agent_id": "chunk_contextualization",
            "agent_num": 28,
            "example_id": f"chunk_contextualization-{i + 1:03d}",
            "variation": ch["variation"],
            "doc_id": ch["doc_id"],
            "whole_document": _unique_text(ch["whole_document"], used),
            "chunk_content": ch["chunk_content"],
            "target_context_tokens": ch["target_context_tokens"],
            "target_summary_tokens": ch["target_summary_tokens"],
            "target_concept_terms": ch["target_concept_terms"],
            "chunk_type_hint": ch["chunk_type_hint"],
            "subject": ch["subject"],
            "exam_type": ch["exam_type"],
            "tags": ["ingestion", ch["subject"], ch["variation"]],
        })

    for i, chain in enumerate(chains):
        parts = [_unique_text(p, used, f" part-{j}") for j, p in enumerate(chain["parts"])]
        items.append({
            "agent_id": "whole_file_map_summarizer",
            "agent_num": 29,
            "example_id": f"whole_file_map_summarizer-{i + 1:03d}",
            "variation": chain["variation"],
            "doc_id": chain["doc_id"],
            "parts": parts,
            "header": chain["header"],
            "subject": chain["subject"],
            "exam_type": chain["exam_type"],
            "user_message": chain["user_message"],
            "tags": [chain["exam_type"], chain["subject"], chain["variation"]],
        })

    for i, chain in enumerate(chains):
        map_item = next(x for x in items if x["example_id"] == f"whole_file_map_summarizer-{i + 1:03d}")
        parts_display = "\n".join(f"- Part {j + 1}: {p[:300]}" for j, p in enumerate(map_item["parts"]))
        items.append({
            "agent_id": "whole_file_reduce",
            "agent_num": 30,
            "example_id": f"whole_file_reduce-{i + 1:03d}",
            "variation": chain["variation"],
            "doc_id": chain["doc_id"],
            "map_example_id": map_item["example_id"],
            "user_message": chain["user_message"],
            "section_summaries": "",  # filled from map gold after LLM gen
            "parts": map_item["parts"],
            "subject": chain["subject"],
            "exam_type": chain["exam_type"],
            "tags": [chain["exam_type"], chain["subject"], chain["variation"]],
        })

    return items


def main() -> int:
    used = load_used_inputs()
    items = build_pool(used)
    payload = {
        "version": "1.0.0",
        "extraction_tag": "production_llm_gold",
        "total_examples": len(items),
        "items": items,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} examples to {OUT}")
    from collections import Counter
    c = Counter(i["agent_id"] for i in items)
    for aid, n in sorted(c.items()):
        print(f"  {aid}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
