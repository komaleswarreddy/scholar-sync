#!/usr/bin/env python3
"""Strict verification for Agents 26–30 dataset."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
POOL = SCRIPTS / "agents_26_30_eval_pool.json"
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
COMPLETE_MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

TARGETS = {
    "document_sketch": 13,
    "ncert_document_sketch": 13,
    "chunk_contextualization": 13,
    "whole_file_map_summarizer": 13,
    "whole_file_reduce": 13,
}

CHUNK_TYPES = {
    "definition", "procedure", "example", "table", "figure",
    "argument", "formula", "qa", "other",
}

PLACEHOLDER_PATTERNS = [
    r"Main idea of section",
    r"Synthesis of \d+ parts",
    r"Ohm's law",
]


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _source_text(item: dict[str, Any]) -> str:
    parts = " ".join(item.get("parts") or [])
    return (item.get("document_text") or item.get("whole_document") or parts or "").lower()


def _check_sketch(gold: dict[str, Any], item: dict[str, Any], ex: str, failures: list[str]) -> None:
    sketch = gold.get("sketch_json", {})
    concepts = sketch.get("concepts") or []
    if len(concepts) < 10:
        failures.append(f"{ex}: concepts count {len(concepts)} < 10")
    defs = sketch.get("key_definitions") or {}
    doc = (item.get("document_text") or "").lower()
    for term in defs:
        if "ohm" in str(term).lower() and "ohm" not in doc and "electric" not in doc:
            subj = (item.get("subject") or "").lower()
            if "electric" not in subj and "physics" not in subj:
                failures.append(f"{ex}: Ohm leak in non-electricity sketch")


def _check_contextualization(gold: dict[str, Any], item: dict[str, Any], ex: str, failures: list[str]) -> None:
    for k in ("target_context_tokens", "target_summary_tokens", "target_concept_terms"):
        if k not in item:
            failures.append(f"{ex}: missing input {k}")
    ctx = gold.get("contextualization_json", {})
    ctype = str(ctx.get("chunk_type", "")).lower()
    if ctype not in CHUNK_TYPES:
        failures.append(f"{ex}: invalid chunk_type {ctype}")


def _check_map(gold: dict[str, Any], item: dict[str, Any], ex: str, failures: list[str]) -> None:
    parts = item.get("parts") or []
    text = gold.get("map_summaries", "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    part_lines = [ln for ln in lines if re.match(r"^Part\s+\d+", ln, re.I)]
    if len(part_lines) != len(parts):
        failures.append(f"{ex}: map lines {len(part_lines)} != parts {len(parts)}")
    for pat in PLACEHOLDER_PATTERNS[:1]:
        if re.search(pat, text, re.I):
            failures.append(f"{ex}: placeholder map pattern")


def _check_reduce(gold: dict[str, Any], item: dict[str, Any], ex: str, failures: list[str]) -> None:
    ans = gold.get("final_answer", "")
    if len(ans) < 120:
        failures.append(f"{ex}: final_answer too short")
    summaries = gold.get("section_summaries") or item.get("section_summaries") or ""
    if not summaries.strip():
        failures.append(f"{ex}: missing section_summaries")
    for pat in (r"Synthesis of \d+ parts",):
        if re.search(pat, ans, re.I):
            failures.append(f"{ex}: placeholder reduce pattern")


def main() -> int:
    failures: list[str] = []
    if not POOL.exists():
        print(f"Missing {POOL}", file=sys.stderr)
        return 1
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    items = pool["items"]

    by_agent = Counter(i["agent_id"] for i in items)
    for aid, n in TARGETS.items():
        if by_agent[aid] != n:
            failures.append(f"{aid}: expected {n} examples, got {by_agent[aid]}")

    llm_count = sum(1 for i in items if i.get("gold_source") == "production_llm" and i.get("llm_gold"))
    if llm_count != 65:
        failures.append(f"production_llm gold: {llm_count}/65")

    input_norms: list[str] = []
    for i in items:
        aid = i["agent_id"]
        if aid in ("document_sketch", "ncert_document_sketch"):
            input_norms.append(normalize((i.get("header") or "") + "|" + (i.get("document_text") or "")[:400]))
        elif aid == "chunk_contextualization":
            input_norms.append(normalize((i.get("chunk_content") or "")[:400]))
        elif aid == "whole_file_map_summarizer":
            input_norms.append(normalize("|".join((i.get("parts") or [])[:2])[:400]))
        elif aid == "whole_file_reduce":
            input_norms.append(normalize((i.get("user_message") or "") + "|" + (i.get("section_summaries") or "")[:200]))
    dup = len(input_norms) - len(set(input_norms))
    if dup:
        failures.append(f"duplicate inputs in pool: {dup}")

    for i in items:
        ex = i["example_id"]
        gold = i.get("llm_gold")
        if not gold:
            failures.append(f"{ex}: missing llm_gold")
            continue
        raw = json.dumps(gold)
        for pat in PLACEHOLDER_PATTERNS:
            if pat == r"Ohm's law":
                doc = _source_text(i)
                if re.search(pat, raw, re.I) and "ohm" not in doc:
                    subj = (i.get("subject") or "").lower()
                    if "electric" not in subj and "physics" not in subj:
                        failures.append(f"{ex}: Ohm placeholder in non-electricity gold")
            elif pat != r"Ohm's law" and re.search(pat, raw, re.I):
                failures.append(f"{ex}: placeholder pattern {pat}")

        aid = i["agent_id"]
        if aid in ("document_sketch", "ncert_document_sketch"):
            _check_sketch(gold, i, ex, failures)
        elif aid == "chunk_contextualization":
            _check_contextualization(gold, i, ex, failures)
        elif aid == "whole_file_map_summarizer":
            _check_map(gold, i, ex, failures)
        elif aid == "whole_file_reduce":
            _check_reduce(gold, i, ex, failures)

    if MD.exists():
        md = MD.read_text(encoding="utf-8")
        if "## 26." not in md:
            failures.append("Complete_Agent_DataSet.md missing Agent 26 section")
        else:
            block = md[md.find("## 26."):]
            for n in (26, 27, 28, 29, 30):
                if f"## {n}." not in block and f"## {n}." not in md:
                    failures.append(f"MD missing Agent {n} section")
            if llm_count == 65 and "thirty-agent" not in md[:2000]:
                failures.append("MD header not updated to thirty-agent")

    print(f"Agents 26-30 verify: {len(failures)} failure(s)")
    for f in failures[:30]:
        print(f"  FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
