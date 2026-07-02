#!/usr/bin/env python3
"""Add image_text / figure_crop (Option A gold copy) to OCR tiered datasets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATCHES = {
    "image_ocr": {
        "path": ROOT / "evals/datasets/prompt_tiered/source_upload/image_ocr.json",
        "input_field": "image_text",
        "ref_field": "extracted_text",
        "extra_input_keys": ["image_text"],
    },
    "diagram_label_ocr": {
        "path": ROOT / "evals/datasets/prompt_tiered/source_upload/diagram_label_ocr.json",
        "input_field": "figure_crop",
        "ref_field": "labels_text",
        "extra_input_keys": ["figure_crop"],
    },
}


def patch_one(cfg: dict) -> int:
    path: Path = cfg["path"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    field = cfg["input_field"]
    ref_field = cfg["ref_field"]
    n = 0
    for item in doc.get("items") or []:
        gold = (item.get("reference_outputs") or {}).get(ref_field)
        if gold is None:
            continue
        item.setdefault("inputs", {})[field] = gold
        n += 1

    langsmith = doc.setdefault("langsmith", {})
    keys = list(langsmith.get("input_keys") or [])
    for k in cfg["extra_input_keys"]:
        if k not in keys:
            keys.append(k)
    langsmith["input_keys"] = keys
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Patched {path.name}: {n} items, input_keys={keys}")
    return n


def main() -> int:
    total = sum(patch_one(cfg) for cfg in PATCHES.values())
    print(f"Total items patched: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
