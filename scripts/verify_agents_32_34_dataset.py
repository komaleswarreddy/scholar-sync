#!/usr/bin/env python3
"""Strict verification for Agents 32–34 dataset."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from packages.core.security.refusal_templates import RefusalReason, RefusalTemplates

POOL = SCRIPTS / "agents_32_34_eval_pool.json"
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

TARGETS = {
    "image_ocr": 13,
    "diagram_label_ocr": 13,
    "refusal_templates": 13,
}

PLACEHOLDER_PATTERNS = [
    r"image_fixture_note",
    r"Section A\\nQ1 Define photosynthesis",
    r"First main idea",
    r"I can't help with dangerous instructions\. Ask about safe",
]


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


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

    llm_count = sum(
        1 for i in items
        if i.get("agent_id") in ("image_ocr", "diagram_label_ocr")
        and i.get("gold_source") == "production_llm"
        and i.get("llm_gold")
    )
    tmpl_count = sum(
        1 for i in items
        if i.get("agent_id") == "refusal_templates"
        and i.get("gold_source") == "production_template"
        and i.get("llm_gold")
    )
    if llm_count != 26:
        failures.append(f"production_llm vision gold: {llm_count}/26")
    if tmpl_count != 13:
        failures.append(f"production_template gold: {tmpl_count}/13")

    input_norms: list[str] = []
    for i in items:
        aid = i["agent_id"]
        if aid == "image_ocr":
            input_norms.append(normalize(f"{i.get('pdf_source')}|{i.get('page_number')}"))
        elif aid == "diagram_label_ocr":
            input_norms.append(
                normalize(
                    f"{i.get('pdf_source')}|{i.get('page_number')}|fig{i.get('figure_index', 0)}"
                )
            )
        else:
            input_norms.append(normalize(f"{i.get('user_message')}|{i.get('scenario')}"))
    dup = len(input_norms) - len(set(input_norms))
    if dup:
        failures.append(f"duplicate inputs in pool: {dup}")

    rt = RefusalTemplates()
    for i in items:
        ex = i["example_id"]
        gold = i.get("llm_gold")
        if not gold:
            failures.append(f"{ex}: missing gold")
            continue
        raw = json.dumps(gold)
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, raw, re.I):
                failures.append(f"{ex}: placeholder pattern {pat}")

        aid = i["agent_id"]
        if aid == "image_ocr":
            text = gold.get("extracted_text", "")
            if len(text) < 40:
                failures.append(f"{ex}: extracted_text too short")
            if i.get("variation") == "diagram" and "[diagram:" not in text.lower():
                failures.append(f"{ex}: diagram variation missing [Diagram: ...] block")
            if "fixture_note" in json.dumps(i.get("inputs", i)).lower():
                failures.append(f"{ex}: image_fixture_note input")
        elif aid == "diagram_label_ocr":
            labels = gold.get("labels_text", "")
            if len(labels) < 15:
                failures.append(f"{ex}: labels_text too short")
            if len(labels) > 900:
                failures.append(f"{ex}: labels_text looks like full OCR")
        elif aid == "refusal_templates":
            scenario = i.get("scenario", "")
            try:
                reason = RefusalReason[scenario]
            except KeyError:
                failures.append(f"{ex}: invalid scenario {scenario}")
                continue
            # Production now rotates among the 3 templates per reason (random by
            # default, or stable-per-user when a variation_key is passed), so gold
            # must match ANY of the reason's templates, not just the first one.
            acceptable = rt.templates.get(reason, [])
            if gold.get("user_facing_message") not in acceptable:
                failures.append(f"{ex}: message not in production templates for {reason.value}")
            if gold.get("refusal_reason") != reason.value:
                failures.append(f"{ex}: refusal_reason mismatch")

    if MD.exists():
        md = MD.read_text(encoding="utf-8")
        if "## 32." not in md:
            failures.append("Complete_Agent_DataSet.md missing Agent 32 section")
        if llm_count == 26 and tmpl_count == 13 and "thirty-three-agent" not in md[:2500]:
            failures.append("MD header not updated to thirty-three-agent")

    print(f"Agents 32-34 verify: {len(failures)} failure(s)")
    for f in failures[:30]:
        print(f"  FAIL: {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
