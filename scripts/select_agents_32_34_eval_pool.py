#!/usr/bin/env python3
"""Build production eval pool for Agents 32–34 (OCR + refusal)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from ocr_eval_catalog import (
    diagram_ocr_entries,
    image_ocr_entries,
    refusal_entries,
    render_figure_fixture,
    render_page_png,
)

from packages.core.security.refusal_templates import RefusalReason, RefusalTemplates

OUT = SCRIPTS / "agents_32_34_eval_pool.json"
COMPLETE_MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_used_inputs() -> set[str]:
    if not COMPLETE_MD.exists():
        return set()
    text = COMPLETE_MD.read_text(encoding="utf-8")
    used: set[str] = set()
    for label in (
        "Pdf Source", "Page Number", "Extracted Text", "Labels Text",
        "User Message", "Scenario",
    ):
        for m in re.finditer(rf"\*\*{label}:\*\*\s*\n\n(.+?)\n\n\*\*", text, re.S):
            used.add(normalize(m.group(1)[:400]))
    return used


def _refusal_gold(user_message: str, scenario: str) -> dict[str, Any]:
    reason = RefusalReason[scenario]
    # get_refusal() now rotates templates (random/per-user). For stable, reproducible
    # gold we deterministically anchor on the first template of the reason; the verifier
    # accepts any of the reason's templates, so production rotation still passes.
    templates = RefusalTemplates().templates[reason]
    return {
        "refusal_reason": reason.value,
        "user_facing_message": templates[0],
    }


def build_pool() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for i, row in enumerate(image_ocr_entries()):
        try:
            render_page_png(row["source_key"], row["page_number"])
            png_path = SCRIPTS / "ocr_eval_fixtures" / f"{row['source_key']}-p{row['page_number']}.png"
        except FileNotFoundError:
            png_path = SCRIPTS / "ocr_eval_fixtures" / f"{row['source_key']}-p{row['page_number']}.png"
        items.append({
            "agent_id": "image_ocr",
            "agent_num": 32,
            "example_id": f"image_ocr-{i + 1:03d}",
            "variation": row["variation"],
            "doc_id": f"{row['source_key']}-p{row['page_number']}",
            "pdf_source": row["pdf_source"],
            "page_number": row["page_number"],
            "source_key": row["source_key"],
            "fixture_path": str(png_path.relative_to(ROOT)).replace("\\", "/"),
            "subject": row["subject"],
            "exam_type": row["exam_type"],
            "tags": ["ocr", row["exam_type"], row["subject"], row["variation"]],
        })

    for i, row in enumerate(diagram_ocr_entries()):
        fig_idx = int(row.get("figure_index", 0))
        try:
            fixture = render_figure_fixture(
                row["source_key"],
                row["page_number"],
                figure_index=fig_idx,
            )
        except FileNotFoundError:
            fixture = SCRIPTS / "ocr_eval_fixtures" / (
                f"{row['source_key']}-p{row['page_number']}-fig{fig_idx}.png"
            )
        items.append({
            "agent_id": "diagram_label_ocr",
            "agent_num": 33,
            "example_id": f"diagram_label_ocr-{i + 1:03d}",
            "variation": row["variation"],
            "doc_id": f"{row['source_key']}-p{row['page_number']}-fig{fig_idx}",
            "pdf_source": row["pdf_source"],
            "page_number": row["page_number"],
            "source_key": row["source_key"],
            "crop_mode": row.get("crop_mode", "embedded_figure"),
            "figure_index": fig_idx,
            "fixture_path": str(fixture.relative_to(ROOT)).replace("\\", "/"),
            "subject": row["subject"],
            "exam_type": row["exam_type"],
            "tags": ["diagram_ocr", row["exam_type"], row["subject"], row["variation"]],
        })

    for i, row in enumerate(refusal_entries()):
        gold = _refusal_gold(row["user_message"], row["scenario"])
        items.append({
            "agent_id": "refusal_templates",
            "agent_num": 34,
            "example_id": f"refusal_templates-{i + 1:03d}",
            "variation": row["variation"],
            "user_message": row["user_message"],
            "scenario": row["scenario"],
            "subject": "safety",
            "exam_type": "guardrail",
            "tags": ["safety", "guardrail", row["variation"]],
            "llm_gold": gold,
            "gold_source": "production_template",
        })

    return items


def main() -> int:
    items = build_pool()
    payload = {
        "version": "1.0.0",
        "extraction_tag": "production_vision_gold",
        "total_examples": len(items),
        "items": items,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} examples to {OUT}")
    from collections import Counter
    for aid, n in sorted(Counter(i["agent_id"] for i in items).items()):
        print(f"  {aid}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
