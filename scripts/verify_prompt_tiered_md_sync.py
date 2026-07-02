#!/usr/bin/env python3
"""Verify evals/datasets/prompt_tiered/*.json are pin-to-pin in sync with the
source of truth: Reference dataset/Complete_Agent_DataSet.md.

Read-only. Uses the same parsing rules as scripts/sync_prompt_tiered_from_md.py.

Usage:
    python scripts/verify_prompt_tiered_md_sync.py            # all datasets
    python scripts/verify_prompt_tiered_md_sync.py image_ocr  # one dataset
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from sync_prompt_tiered_from_md import (  # noqa: E402
    MD_PATH,
    OUTPUT_DIR,
    SNO_TO_SLUG,
    build_reference_outputs,
    parse_evaluators,
    parse_fields,
    parse_langsmith_keys,
    parse_variation_and_tags,
    split_examples,
    split_region,
)

SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)


def norm_text(s: str) -> str:
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.split("\n")]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def norm_struct(value: Any) -> Any:
    if isinstance(value, str):
        return norm_text(value)
    if isinstance(value, list):
        return [norm_struct(v) for v in value]
    if isinstance(value, dict):
        return {k: norm_struct(v) for k, v in sorted(value.items())}
    return value


def load_md_sections() -> dict[int, str]:
    text = MD_PATH.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    sections: dict[int, str] = {}
    for i, m in enumerate(matches):
        sno = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[sno] = text[start:end]
    return sections


def parse_md_example(block: str, output_keys: list[str]) -> dict[str, Any]:
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
    return {
        "variation": variation,
        "tags": tags,
        "inputs": inputs,
        "reference_outputs": reference_outputs,
        "evaluators": evaluators,
    }


def compare_dataset(slug: str, section: str) -> list[str]:
    errors: list[str] = []
    matches = list(OUTPUT_DIR.rglob(f"{slug}.json"))
    if not matches:
        return [f"{slug}: dataset JSON file not found"]
    data = json.loads(matches[0].read_text(encoding="utf-8"))
    items = data.get("items", [])
    _, output_keys = parse_langsmith_keys(section)

    md_examples = split_examples(section)
    md_ids = [eid for eid, _ in md_examples]
    json_ids = [it.get("id") for it in items]

    if set(json_ids) != set(md_ids):
        only_md = sorted(set(md_ids) - set(json_ids))
        only_json = sorted(set(json_ids) - set(md_ids))
        if only_md:
            errors.append(f"{slug}: example IDs in MD but missing from JSON: {only_md}")
        if only_json:
            errors.append(f"{slug}: example IDs in JSON but missing from MD: {only_json}")
    if len(md_ids) != len(json_ids):
        errors.append(f"{slug}: example count MD={len(md_ids)} JSON={len(json_ids)}")

    json_by_id = {it.get("id"): it for it in items}
    for ex_id, block in md_examples:
        if ex_id not in json_by_id:
            continue
        md_item = parse_md_example(block, output_keys)
        js_item = json_by_id[ex_id]

        if md_item["variation"] and md_item["variation"] != js_item.get("variation"):
            errors.append(
                f"{slug}/{ex_id}: variation MD='{md_item['variation']}' "
                f"JSON='{js_item.get('variation')}'"
            )
        if md_item["tags"] != js_item.get("tags", []):
            errors.append(f"{slug}/{ex_id}: tags mismatch")
        if norm_struct(md_item["inputs"]) != norm_struct(js_item.get("inputs", {})):
            errors.append(f"{slug}/{ex_id}: inputs mismatch")
        if norm_struct(md_item["reference_outputs"]) != norm_struct(
            js_item.get("reference_outputs", {})
        ):
            errors.append(f"{slug}/{ex_id}: reference_outputs mismatch")
        if md_item["evaluators"] and md_item["evaluators"] != js_item.get("evaluators", []):
            errors.append(f"{slug}/{ex_id}: evaluators mismatch")
    return errors


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else None
    sections = load_md_sections()
    all_errors: list[str] = []
    ok: list[str] = []
    pending: list[str] = []

    for sno, slug in sorted(SNO_TO_SLUG.items()):
        if target and slug != target:
            continue
        if sno not in sections:
            all_errors.append(f"{slug}: MD section ## {sno}. not found")
            continue
        errs = compare_dataset(slug, sections[sno])
        if errs:
            pending.append(slug)
            all_errors.extend(errs)
        else:
            ok.append(slug)

    print("=" * 70)
    print(f"MD<->JSON sync check  (source of truth: {MD_PATH.name})")
    print("=" * 70)
    print(f"In sync ({len(ok)}): {', '.join(ok) if ok else '-'}")
    print(f"Out of sync ({len(pending)}): {', '.join(pending) if pending else '-'}")
    if all_errors:
        print("\nMismatches:")
        for e in all_errors:
            print(f"  FAIL: {e}")
    print(f"\nTotal mismatches: {len(all_errors)}")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
